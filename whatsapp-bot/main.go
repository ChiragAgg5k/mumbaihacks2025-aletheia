package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"mime/multipart"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	_ "github.com/mattn/go-sqlite3"
	"github.com/mdp/qrterminal/v3"
	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/proto/waE2E"
	"go.mau.fi/whatsmeow/store/sqlstore"
	"go.mau.fi/whatsmeow/types/events"
	waLog "go.mau.fi/whatsmeow/util/log"
	"google.golang.org/protobuf/proto"
)

// Config holds the bot configuration
type Config struct {
	BackendURL string
}

// AnalyzeRequest is the request body for the backend API
type AnalyzeRequest struct {
	Text string `json:"text"`
}

// AnalyzeResponse is the response from the backend API
type AnalyzeResponse struct {
	IsMisinformation bool     `json:"is_misinformation"`
	Confidence       float64  `json:"confidence"`
	IsNews           bool     `json:"is_news"`
	Summary          string   `json:"summary"`
	Evidence         []string `json:"evidence"`
	SourcesChecked   []string `json:"sources_checked"`
	Recommendation   string   `json:"recommendation"`
	MessageType      string   `json:"message_type"`
}

var (
	client *whatsmeow.Client
	config Config
)

func init() {
	config = Config{
		BackendURL: getEnv("BACKEND_URL", "http://localhost:8000"),
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// analyzeText calls the backend API to analyze text for misinformation
func analyzeText(text string) (*AnalyzeResponse, error) {
	reqBody := AnalyzeRequest{Text: text}
	jsonBody, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	resp, err := http.Post(
		fmt.Sprintf("%s/analyze/text", config.BackendURL),
		"application/json",
		bytes.NewBuffer(jsonBody),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to call backend: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("backend returned status %d", resp.StatusCode)
	}

	var result AnalyzeResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// formatResponse formats the analysis result for WhatsApp
func formatResponse(result *AnalyzeResponse) string {
	var emoji, status string
	
	if result.IsMisinformation {
		if result.Confidence > 0.7 {
			emoji = "🚨"
			status = "LIKELY MISINFORMATION"
		} else {
			emoji = "⚠️"
			status = "POTENTIALLY MISLEADING"
		}
	} else {
		emoji = "✅"
		status = "APPEARS CREDIBLE"
	}

	// Create confidence bar
	filled := int(result.Confidence * 10)
	bar := ""
	for i := 0; i < 10; i++ {
		if i < filled {
			bar += "█"
		} else {
			bar += "░"
		}
	}

	response := fmt.Sprintf("%s *%s*\n\n*Confidence:* [%s] %.0f%%\n",
		emoji, status, bar, result.Confidence*100)

	if result.Summary != "" {
		response += fmt.Sprintf("\n*Summary:*\n%s\n", result.Summary)
	}

	if len(result.Evidence) > 0 {
		response += "\n*Evidence:*\n"
		for i, e := range result.Evidence {
			if i >= 3 {
				break
			}
			response += fmt.Sprintf("• %s\n", e)
		}
	}

	if len(result.SourcesChecked) > 0 {
		response += "\n*Sources:*\n"
		for i, s := range result.SourcesChecked {
			if i >= 3 {
				break
			}
			response += fmt.Sprintf("• %s\n", s)
		}
	}

	if result.Recommendation != "" {
		response += fmt.Sprintf("\n*Recommendation:*\n%s\n", result.Recommendation)
	}

	response += "\n_Always verify important news from multiple credible sources._"

	return response
}

// analyzeImage calls the backend API to analyze an image for misinformation
func analyzeImage(imageData []byte) (*AnalyzeResponse, error) {
	// Create multipart form
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)
	
	part, err := writer.CreateFormFile("file", "image.jpg")
	if err != nil {
		return nil, fmt.Errorf("failed to create form file: %w", err)
	}
	
	_, err = part.Write(imageData)
	if err != nil {
		return nil, fmt.Errorf("failed to write image data: %w", err)
	}
	
	err = writer.Close()
	if err != nil {
		return nil, fmt.Errorf("failed to close writer: %w", err)
	}
	
	req, err := http.NewRequest("POST", fmt.Sprintf("%s/analyze/image", config.BackendURL), &buf)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Content-Type", writer.FormDataContentType())
	
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to call backend: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("backend returned status %d", resp.StatusCode)
	}
	
	var result AnalyzeResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	
	return &result, nil
}

// handleMessage processes incoming messages
func handleMessage(evt *events.Message) {
	msg := evt.Message
	
	// Check for image message
	if msg.GetImageMessage() != nil {
		handleImageMessage(evt)
		return
	}
	
	// Get the message text
	text := ""

	if msg.GetConversation() != "" {
		text = msg.GetConversation()
	} else if msg.GetExtendedTextMessage() != nil {
		text = msg.GetExtendedTextMessage().GetText()
	}

	// Ignore empty or very short messages
	if len(text) < 10 {
		return
	}

	fmt.Printf("Received message from %s: %s\n", evt.Info.Sender.String(), text)

	// Analyze the message
	result, err := analyzeText(text)
	if err != nil {
		fmt.Printf("Error analyzing message: %v\n", err)
		sendMessage(evt, "❌ *Error*\n\nCould not connect to the analysis backend. Please try again later.")
		return
	}

	// If not news, silently ignore
	if !result.IsNews {
		fmt.Printf("Not news, ignoring: %s\n", text)
		return
	}

	// Send the response
	response := formatResponse(result)
	sendMessage(evt, response)
}

// handleImageMessage processes incoming image messages
func handleImageMessage(evt *events.Message) {
	fmt.Printf("Received image from %s\n", evt.Info.Sender.String())
	
	imgMsg := evt.Message.GetImageMessage()
	if imgMsg == nil {
		return
	}
	
	// Download the image
	data, err := client.Download(context.Background(), imgMsg)
	if err != nil {
		fmt.Printf("Error downloading image: %v\n", err)
		sendMessage(evt, "❌ *Error*\n\nCould not download the image. Please try again.")
		return
	}
	
	// Analyze the image
	result, err := analyzeImage(data)
	if err != nil {
		fmt.Printf("Error analyzing image: %v\n", err)
		sendMessage(evt, "❌ *Error*\n\nCould not analyze the image. Please try again later.")
		return
	}
	
	// Send the response
	response := formatResponse(result)
	sendMessage(evt, response)
}

// sendMessage sends a reply to the specific message
func sendMessage(evt *events.Message, text string) {
	// Create context info to quote/reply to the original message
	contextInfo := &waE2E.ContextInfo{
		StanzaID:      proto.String(evt.Info.ID),
		Participant:   proto.String(evt.Info.Sender.String()),
		QuotedMessage: evt.Message,
	}

	msg := &waE2E.Message{
		ExtendedTextMessage: &waE2E.ExtendedTextMessage{
			Text:        proto.String(text),
			ContextInfo: contextInfo,
		},
	}

	_, err := client.SendMessage(context.Background(), evt.Info.Chat, msg)
	if err != nil {
		fmt.Printf("Error sending message: %v\n", err)
	}
}

// eventHandler handles all WhatsApp events
func eventHandler(evt interface{}) {
	switch v := evt.(type) {
	case *events.Message:
		// Only handle messages from others (not our own)
		if !v.Info.IsFromMe {
			handleMessage(v)
		}
	case *events.Connected:
		fmt.Println("✅ Connected to WhatsApp!")
	case *events.Disconnected:
		fmt.Println("❌ Disconnected from WhatsApp")
	case *events.LoggedOut:
		fmt.Println("🚪 Logged out from WhatsApp")
	}
}

func main() {
	fmt.Println("🤖 Aletheia WhatsApp Bot - Fake News Detection")
	fmt.Println("================================================")

	// Set up database for session storage
	dbLog := waLog.Stdout("Database", "WARN", true)
	ctx := context.Background()
	
	container, err := sqlstore.New(ctx, "sqlite3", "file:whatsapp_session.db?_foreign_keys=on", dbLog)
	if err != nil {
		fmt.Printf("Failed to create database: %v\n", err)
		os.Exit(1)
	}

	// Get device store
	deviceStore, err := container.GetFirstDevice(ctx)
	if err != nil {
		fmt.Printf("Failed to get device: %v\n", err)
		os.Exit(1)
	}

	// Create client
	clientLog := waLog.Stdout("Client", "WARN", true)
	client = whatsmeow.NewClient(deviceStore, clientLog)
	client.AddEventHandler(eventHandler)

	// Check if we need to login
	if client.Store.ID == nil {
		// New login - show QR code
		qrChan, _ := client.GetQRChannel(context.Background())
		err = client.Connect()
		if err != nil {
			fmt.Printf("Failed to connect: %v\n", err)
			os.Exit(1)
		}

		fmt.Println("\n📱 Scan this QR code with WhatsApp to login:")
		fmt.Println("   (WhatsApp > Settings > Linked Devices > Link a Device)")
		fmt.Println()

		for evt := range qrChan {
			if evt.Event == "code" {
				qrterminal.GenerateHalfBlock(evt.Code, qrterminal.L, os.Stdout)
			} else {
				fmt.Println("Login event:", evt.Event)
			}
		}
	} else {
		// Already logged in
		err = client.Connect()
		if err != nil {
			fmt.Printf("Failed to connect: %v\n", err)
			os.Exit(1)
		}
	}

	fmt.Println("\n✅ Bot is running! Send any message to analyze it for misinformation.")
	fmt.Println("   Press Ctrl+C to stop.\n")

	// Wait for interrupt signal
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	<-c

	fmt.Println("\n👋 Shutting down...")
	client.Disconnect()
}
