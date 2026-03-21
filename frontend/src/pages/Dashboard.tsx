import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { useToast } from "@/hooks/use-toast";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Send, 
  LogOut, 
  Sparkles, 
  MessageCircle, 
  Plus,
  Trash2,
  AlertCircle,
  Wifi,
  WifiOff,
  Calendar,
  Gift,
  TrendingUp,
  X,
  Mail
} from "lucide-react";
import { chatbotApi, checkBackendConnection, type Chat as ApiChat, type Message as ApiMessage } from "@/lib/chatbot-api";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Festival {
  name: string;
  date: string;
  category: string;
  days_until: number;
  is_today: boolean;
  recommendations: {
    stock_updates: string[];
    discount_suggestions: string[];
    marketing_tips: string[];
  };
}

const Dashboard = () => {
  // Default admin questions grouped by category
  const defaultQuestions = [
    {
      category: '🟣 Business Overview',
      questions: [
        'What is the largest single order placed (by quantity)?',
        'Which customer has ordered the maximum quantity overall?',
        'Who are the top 3 customers?',
        'What is the total number of cancelled orders?',
        'How many agents are handling orders?',
      ],
    },
    {
      category: '👤 Customer Insights',
      questions: [
        'Which customers have placed multiple orders?',
        'Who are the customers that ordered the same composition but at different rates?',
        'Which customer has the highest number of confirmed orders?',
        'Are there customers who have only 0.0 rate orders?',
      ],
    },
    {
      category: '🧑‍💼 Agent Insights',
      questions: [
        'Which agent generated the highest revenue?',
        'Who are the customers handled by multiple agents?',
        'Which agent managed the maximum variety of weave types?',
      ],
    },
    {
      category: '🕒 Order & Trend Monitoring',
      questions: [
        'Which date had the highest number of orders?',
        'How many orders were placed in the current month?',
        'What is the difference in total quantity between confirmed and processed orders?',
      ],
    },
  ];

  // Handles clicking a default question button
  const handleDefaultQuestionClick = async (question: string) => {
    if (!isBackendConnected) return;
    let chatId = currentChatId;
    // Create new chat if none exists
    if (!chatId) {
      const response = await chatbotApi.createNewChat();
      if (response.success && response.data) {
        setChats(prev => [response.data!, ...prev]);
        chatId = response.data!.id;
        setCurrentChatId(chatId);
      } else {
        toast({ title: 'Error', description: response.error || 'Failed to create chat', variant: 'destructive' });
        return;
      }
    }
    setNewMessage("");
    setIsTyping(true);
    try {
      const messageResponse = await chatbotApi.sendMessage(chatId, question, selectedLanguage);
      if (messageResponse.success && messageResponse.data) {
        setChats(prev => prev.map(chat => chat.id === chatId ? messageResponse.data!.chat : chat));
        // Scroll to chat area
        const chatArea = document.querySelector('.chat-messages');
        if (chatArea) chatArea.scrollIntoView({ behavior: 'smooth' });
      } else {
        throw new Error(messageResponse.error || 'Failed to send message');
      }
    } catch (error: any) {
      toast({ title: 'Error', description: error.message || 'Failed to send message', variant: 'destructive' });
    } finally {
      setIsTyping(false);
    }
  };
  const [chats, setChats] = useState<ApiChat[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [newMessage, setNewMessage] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState("en"); // en, ta, hi
  const [isTyping, setIsTyping] = useState(false);
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [isCheckingConnection, setIsCheckingConnection] = useState(true);
  const [upcomingFestivals, setUpcomingFestivals] = useState<Festival[]>([]);
  const [showFestivalPopup, setShowFestivalPopup] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();

  const currentChat = chats.find(chat => chat.id === currentChatId);

  // Load upcoming festivals - now triggered 1 second after login
  const loadFestivals = async () => {
    try {
      const response = await chatbotApi.getUpcomingFestivals();
      if (response.success && response.data) {
        setUpcomingFestivals(response.data);
        // Show popup if there are upcoming festivals
        if (response.data.length > 0) {
          setShowFestivalPopup(true);
        }
      }
    } catch (error) {
      console.error('Failed to load festivals:', error);
    }
  };

  // Check backend connection on component mount
  useEffect(() => {
    const checkConnection = async () => {
      setIsCheckingConnection(true);
      const connected = await checkBackendConnection();
      setIsBackendConnected(connected);
      setIsCheckingConnection(false);
      
      if (!connected) {
        toast({
          title: "Backend Connection Failed",
          description: "Please make sure the Python backend server is running on port 8000",
          variant: "destructive",
        });
      } else {
        // Load existing chats when connected
        loadChats();
        // Note: Festival notifications will be handled by authentication useEffect
      }
    };
    
    checkConnection();
  }, [toast]);

  useEffect(() => {
    const isAuthenticated = localStorage.getItem("isAuthenticated");
    if (!isAuthenticated) {
      navigate("/");
    } else {
      // Show festival notification exactly 1 second after login
      const hasShownFestivalNotification = sessionStorage.getItem("festivalNotificationShown");
      
      if (!hasShownFestivalNotification) {
        setTimeout(() => {
          // Load festivals and show notification
          loadFestivals().then(() => {
            // Mark as shown for this session
            sessionStorage.setItem("festivalNotificationShown", "true");
          });
        }, 100); // Show exactly 1 second after login
      }
    }
  }, [navigate]);

  const loadChats = async () => {
    try {
      const response = await chatbotApi.getAllChats();
      if (response.success && response.data) {
        setChats(response.data);
      }
    } catch (error) {
      console.error("Failed to load chats:", error);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("isAuthenticated");
    // Clear session storage to reset notifications for next login
    sessionStorage.removeItem("festivalNotificationShown");
    sessionStorage.removeItem("festivalAcknowledged");
    // Toast notification removed - no popup for logout
    navigate("/");
  };

  const sendMail = async () => {
    if (!isBackendConnected) {
      toast({
        title: "Backend Not Connected",
        description: "Please check your backend connection",
        variant: "destructive",
      });
      return;
    }

    try {
      const response = await chatbotApi.sendMail();
      if (response.success) {
        toast({
          title: "Email Form Opened",
          description: "The email form has been opened in your default browser",
        });
      } else {
        throw new Error(response.error || "Failed to open email form");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to open email form",
        variant: "destructive",
      });
    }
  };

  const generateFestivalMessage = () => {
    if (upcomingFestivals.length === 0) {
      return "No upcoming festivals to discuss";
    } else if (upcomingFestivals.length === 1) {
      return `Give me business strategies for ${upcomingFestivals[0].name}`;
    } else {
      const festivalNames = upcomingFestivals.map(festival => festival.name);
      return `Give me business strategies for ${festivalNames.join(" and ")}`;
    }
  };

  const handleGoToChat = async () => {
    // Close the festival popup immediately
    setShowFestivalPopup(false);
    
    if (!isBackendConnected || upcomingFestivals.length === 0) {
      return;
    }

    try {
      let chatId = currentChatId;
      
      // Create new chat if none exists
      if (!chatId) {
        const response = await chatbotApi.createNewChat();
        if (response.success && response.data) {
          setChats(prev => [response.data!, ...prev]);
          chatId = response.data!.id;
          setCurrentChatId(chatId);
        } else {
          throw new Error(response.error || "Failed to create chat");
        }
      }

      // Generate and send the festival message
      const festivalMessage = generateFestivalMessage();
      setIsTyping(true);
      
      const messageResponse = await chatbotApi.sendMessage(chatId, festivalMessage, selectedLanguage);
       
      if (messageResponse.success && messageResponse.data) {
        // Update the chat with new messages
        setChats(prev => prev.map(chat =>
          chat.id === chatId ? messageResponse.data!.chat : chat
        ));
        
        // Scroll to the chat area (for mobile)
        const chatArea = document.querySelector('.chat-messages');
        if (chatArea) {
          chatArea.scrollIntoView({ behavior: 'smooth' });
        }
      } else {
        throw new Error(messageResponse.error || "Failed to send message");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to start chat conversation",
        variant: "destructive",
      });
    } finally {
      setIsTyping(false);
    }
  };

  const handleRemindLater = () => {
    // Close the festival popup immediately
    setShowFestivalPopup(false);
    
    // Show a toast notification for remind later action
    toast({
      title: "Festival Reminder Set",
      description: "You'll be reminded about upcoming festivals when you log in next time",
      duration: 3000,
    });
  };

  const handleGotIt = () => {
    // Close the festival popup immediately
    setShowFestivalPopup(false);
    
    // Mark that user has acknowledged the festival notifications for this session
    sessionStorage.setItem("festivalAcknowledged", "true");
    
    // Show a brief confirmation
    toast({
      title: "Festival Notifications Acknowledged",
      description: "You're all set! Use the chatbot for festival business strategies.",
      duration: 3000,
    });
  };

  const createNewChat = async () => {
    if (!isBackendConnected) {
      toast({
        title: "Backend Not Connected",
        description: "Please check your backend connection",
        variant: "destructive",
      });
      return;
    }

    try {
      const response = await chatbotApi.createNewChat();
      if (response.success && response.data) {
        setChats(prev => [response.data!, ...prev]);
        setCurrentChatId(response.data!.id);
        toast({
          title: "New Chat Created",
          description: "You can now start your analysis.",
          variant: "default",
        });
      } else {
        throw new Error(response.error || "Failed to create chat");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to create new chat",
        variant: "destructive",
      });
    }
  };

  const deleteChat = async (chatId: string) => {
    try {
      const response = await chatbotApi.deleteChat(chatId);
      if (response.success) {
        setChats(prev => prev.filter(chat => chat.id !== chatId));
        if (currentChatId === chatId) {
          setCurrentChatId(null);
        }
        // Toast notification removed - no popup for chat deletion
      } else {
        throw new Error(response.error || "Failed to delete chat");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to delete chat",
        variant: "destructive",
      });
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !currentChatId || !isBackendConnected) return;

    const messageText = newMessage.trim();
    setNewMessage("");
    setIsTyping(true);

    try {
      const response = await chatbotApi.sendMessage(currentChatId, messageText, selectedLanguage);
       
      if (response.success && response.data) {
        // Update the chat with new messages
        setChats(prev => prev.map(chat =>
          chat.id === currentChatId ? response.data!.chat : chat
        ));
        
        // Toast notification removed - no popup for successful responses
      } else {
        throw new Error(response.error || "Failed to send message");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to send message",
        variant: "destructive",
      });
      
      // Re-add the message to input if it failed
      setNewMessage(messageText);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: any) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  if (isCheckingConnection) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Sparkles className="h-8 w-8 mx-auto mb-4 text-primary animate-pulse" />
          <p className="text-muted-foreground">Connecting to backend...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col md:flex-row">
      {/* Backend Connection Status */}
      {!isBackendConnected && (
        <div className="p-4 bg-destructive/10 border-b border-destructive/20">
          <Alert className="border-destructive/20 bg-destructive/10">
            <WifiOff className="h-4 w-4" />
            <AlertDescription>
              Backend server not connected. Please run: <code className="font-mono">python flask_server.py</code>
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Mobile Header */}
      <div className="md:hidden p-4 border-b border-border bg-card flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          <h1 className="text-lg font-semibold">Sales Chatbot</h1>
          <ScrollArea className="max-h-[440px] pr-4" style={{ scrollbarWidth: 'thin' }}>
            {isBackendConnected ? (
              <Wifi className="h-4 w-4 text-green-500" />
            ) : (
              <WifiOff className="h-4 w-4 text-red-500" />
            )}
          </ScrollArea>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="text-muted-foreground hover:text-foreground"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Sidebar - Hidden on mobile, shown on desktop */}
      <div className="hidden md:flex w-80 bg-card border-r border-border flex-col">
        {/* Desktop Header */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-6 w-6 text-primary" />
              <h1 className="text-lg font-semibold">Sales Chatbot</h1>
              {isBackendConnected ? (
                <Wifi className="h-4 w-4 text-green-500" />
              ) : (
                <WifiOff className="h-4 w-4 text-red-500" />
              )}
            </div>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="text-muted-foreground hover:text-foreground"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
          
          <div className="space-y-2">
            <Button 
              onClick={() => sendMail()}
              disabled={!isBackendConnected}
              className="w-full bg-gradient-primary hover:opacity-90 transition-smooth"
            >
              <Mail className="h-4 w-4 mr-2" />
              Send Mail
            </Button>
            <Button
              onClick={() => window.open('http://localhost:3000/livechat/index.html', '_blank')}
              disabled={!isBackendConnected}
              className="w-full bg-gradient-primary hover:opacity-90 transition-smooth"
            >
              <MessageCircle className="h-4 w-4 mr-2" />
              LiveChat
            </Button>
            
            <Button 
              onClick={createNewChat}
              disabled={!isBackendConnected}
              className="w-full bg-gradient-primary hover:opacity-90 transition-smooth"
            >
              <Plus className="h-4 w-4 mr-2" />
              New Chat
            </Button>
          </div>
        </div>

        {/* Chat List */}
        <ScrollArea className="flex-1 p-2">
          {chats.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground">
              <MessageCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No chats yet</p>
            </div>
          ) : (
            <div className="space-y-1">
              {chats.map((chat) => (
                <div
                  key={chat.id}
                  className={`group p-3 rounded-lg cursor-pointer transition-smooth hover:bg-accent ${
                    currentChatId === chat.id ? "bg-accent" : ""
                  }`}
                  onClick={() => setCurrentChatId(chat.id)}
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium truncate flex-1">
                      {chat.title}
                    </h3>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="opacity-0 group-hover:opacity-100 transition-smooth h-6 w-6 p-0"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteChat(chat.id);
                      }}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {chat.messages.length} messages
                  </p>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </div>

      {/* Mobile New Chat Button */}
      <div className="md:hidden p-4 border-b border-border bg-card">
        <div className="space-y-2">
          <Button 
            onClick={() => sendMail()}
            disabled={!isBackendConnected}
            className="w-full bg-gradient-primary hover:opacity-90 transition-smooth"
          >
            <Mail className="h-4 w-4 mr-2" />
            Send Mail
          </Button>
          
          <Button 
            onClick={createNewChat}
            disabled={!isBackendConnected}
            className="w-full bg-gradient-primary hover:opacity-90 transition-smooth"
          >
            <Plus className="h-4 w-4 mr-2" />
            New Chat
          </Button>
        </div>
      </div>

      {/* Mobile Chat List - Collapsible */}
      {chats.length > 0 && (
        <div className="md:hidden">
          <ScrollArea className="max-h-32 border-b border-border bg-card">
            <div className="p-2 space-y-1">
              {chats.map((chat) => (
                <div
                  key={chat.id}
                  className={`group p-2 rounded-lg cursor-pointer transition-smooth hover:bg-accent flex items-center justify-between ${
                    currentChatId === chat.id ? "bg-accent" : ""
                  }`}
                  onClick={() => setCurrentChatId(chat.id)}
                >
                  <h3 className="text-sm font-medium truncate flex-1">
                    {chat.title}
                  </h3>
                  <div className="flex items-center gap-1">
                    <span className="text-xs text-muted-foreground">
                      {chat.messages.length}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteChat(chat.id);
                      }}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-h-0">
        {currentChat ? (
          <>
            {/* Chat Header - Hidden on mobile to save space */}
            <div className="hidden md:block p-4 border-b border-border bg-card/50">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-lg font-semibold">{currentChat.title}</h2>
                  <p className="text-sm text-muted-foreground">
                    AI-Powered Sales Data Analytics
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Language:</span>
                  <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
                    <SelectTrigger className="w-[120px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en">English</SelectItem>
                      <SelectItem value="ta">தமிழ்</SelectItem>
                      <SelectItem value="hi">हिन्दी</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* Messages */}
            <ScrollArea className="flex-1 p-2 md:p-4 chat-messages">
              <div className="max-w-3xl mx-auto space-y-4">
                {currentChat.messages.length === 0 && (
                  <div className="text-center py-8 md:py-12">
                    <Sparkles className="h-8 w-8 md:h-12 md:w-12 mx-auto mb-4 text-primary" />
                    <h3 className="text-base md:text-lg font-semibold mb-2">Start analyzing your sales data</h3>
                    <p className="text-sm md:text-base text-muted-foreground px-4">
                      Ask me about sales trends, predictions, customer insights, and more!
                    </p>
                  </div>
                )}
                
                {currentChat.messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[85%] md:max-w-xs lg:max-w-md px-3 py-2 md:px-4 md:py-2 rounded-lg transition-smooth ${
                        message.role === "user"
                          ? "bg-chat-bubble-user text-primary-foreground ml-auto"
                          : "bg-chat-bubble-assistant text-foreground"
                      }`}
                    >
                      <div className="text-sm leading-relaxed whitespace-pre-wrap">
                        {message.content}
                      </div>
                      <p className="text-xs opacity-70 mt-1">
                        {formatTimestamp(message.timestamp)}
                      </p>
                    </div>
                  </div>
                ))}

                {isTyping && (
                  <div className="flex justify-start">
                    <div className="bg-chat-bubble-assistant text-foreground px-4 py-2 rounded-lg">
                      <div className="flex items-center gap-1">
                        <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: "0.1s" }}></div>
                        <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>

            {/* Message Input */}
            <div className="p-2 md:p-4 border-t border-border bg-card/50">
              {/* Language selector for mobile */}
              <div className="md:hidden flex justify-end mb-2">
                <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
                  <SelectTrigger className="w-[100px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="ta">தமிழ்</SelectItem>
                    <SelectItem value="hi">हिन्दी</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="max-w-3xl mx-auto flex gap-2">
                <Input
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={isBackendConnected ? "Ask about sales data, trends, predictions..." : "Backend not connected"}
                  className="flex-1 transition-smooth focus:ring-2 focus:ring-primary/20 text-sm md:text-base"
                  disabled={isTyping || !isBackendConnected}
                />
                <Button
                  onClick={sendMessage}
                  disabled={!newMessage.trim() || isTyping || !isBackendConnected}
                  className="bg-gradient-primary hover:opacity-90 transition-smooth shadow-soft h-10 w-10 md:h-auto md:w-auto md:px-4"
                >
                  <Send className="h-4 w-4" />
                  <span className="hidden md:inline ml-2">Send</span>
                </Button>
              </div>
            </div>
          </>
        ) : (
          // Welcome Screen + Default Questions
          <div className="flex-1 flex justify-center" style={{ minHeight: '60vh' }}>
            <div
              className="w-full flex flex-col items-center justify-start"
              style={{ marginTop: '20vh' }}
            >
              <div className="p-4 md:p-6 rounded-full bg-gradient-primary/10 w-16 h-16 md:w-24 md:h-24 flex items-center justify-center mb-4 md:mb-6">
                <Sparkles className="h-8 w-8 md:h-12 md:w-12 text-primary" />
              </div>
              <h2 className="text-xl md:text-2xl font-bold mb-3 bg-gradient-primary bg-clip-text text-transparent text-center">
                Welcome to the Admin Fabric Dashboard! Ready to start your next analysis?
              </h2>
              <div className="h-2" />
              {isBackendConnected ? (
                <div className="flex flex-col items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Language:</span>
                    <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
                      <SelectTrigger className="w-[120px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="en">English</SelectItem>
                        <SelectItem value="ta">தமிழ்</SelectItem>
                        <SelectItem value="hi">हिन्दी</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button
                    onClick={createNewChat}
                    className="bg-gradient-primary hover:opacity-90 transition-smooth shadow-soft w-full md:w-auto mt-4 text-base font-semibold px-6 py-3"
                  >
                    Start New Analysis
                  </Button>
                </div>
              ) : (
                <Alert className="max-w-md mx-auto mt-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Please start the backend server to begin analysis
                  </AlertDescription>
                </Alert>
              )}

              {/* Default Questions Section */}
              <div className="mx-[10%] w-[80%] mt-10">
                <h3 className="text-lg md:text-xl font-bold mb-6 text-center text-primary">Default Questions</h3>
                <div className="space-y-[2%]">
                  {defaultQuestions.map((cat, idx) => (
                    <div key={cat.category} className="mb-8">
                      <h4 className="font-semibold text-base md:text-lg mb-4 text-purple-700 dark:text-purple-300 flex items-center gap-2">
                        {cat.category}
                      </h4>
                      <div className="space-y-[2%]">
                        {cat.questions.map((q, qidx) => (
                          <Button
                            key={q}
                            onClick={() => handleDefaultQuestionClick(q)}
                            className="w-full px-6 py-4 rounded-lg bg-gradient-to-r from-purple-500 to-pink-500 text-white text-base font-medium whitespace-normal text-left shadow-soft hover:from-purple-400 hover:to-pink-400 hover:shadow-lg transition-smooth"
                            style={{ minHeight: '52px' }}
                          >
                            {q}
                          </Button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Festival Notifications Popup Modal */}
      <Dialog open={showFestivalPopup} onOpenChange={setShowFestivalPopup}>
        <DialogContent className="max-w-[95vw] w-[900px] max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader className="px-6 py-6 border-b border-border">
            <DialogTitle className="flex items-center gap-3 text-orange-800 dark:text-orange-200 text-2xl font-bold">
              <Calendar className="h-7 w-7" />
              <span>Upcoming Festivals & Events</span>
            </DialogTitle>
            <DialogDescription className="text-lg mt-3 text-orange-700 dark:text-orange-300 font-medium">
              <span className="inline-flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                Update your inventory and promotions to maximize festival sales!
              </span>
            </DialogDescription>
          </DialogHeader>
          
          {/* Scrollable Content Area */}
          <div className="flex-1 overflow-hidden">
            <ScrollArea className="h-full px-6 py-4">
              <div className="space-y-6 pr-4">
                {upcomingFestivals.map((festival, index) => (
                  <div key={index} className="bg-gradient-to-r from-orange-50 to-red-50 dark:from-orange-950/20 dark:to-red-950/20 rounded-xl p-6 border border-orange-200 dark:border-orange-800 shadow-md">
                    {/* Festival Header */}
                    <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
                      <div className="flex items-center gap-4">
                        <div className="p-2 bg-orange-100 dark:bg-orange-900/50 rounded-full">
                          <Gift className="h-6 w-6 text-orange-600" />
                        </div>
                        <div>
                          <h3 className="font-bold text-xl text-gray-900 dark:text-white mb-2">
                            {festival.name}
                          </h3>
                          <span className="inline-block px-3 py-1 bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-300 rounded-full text-sm font-semibold">
                            {festival.category}
                          </span>
                        </div>
                      </div>
                      <div className="text-center md:text-right">
                        <span className="text-lg font-bold text-orange-600 bg-white/80 dark:bg-gray-800/80 px-4 py-2 rounded-full">
                          {festival.is_today ? "🎉 Today!" : `⏰ ${festival.days_until} days`}
                        </span>
                      </div>
                    </div>
                    
                    {/* Recommendations Grid */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                      {/* Stock Updates */}
                      {festival.recommendations.stock_updates.length > 0 && (
                        <div className="bg-white/90 dark:bg-gray-900/90 rounded-lg p-5 border border-blue-200 dark:border-blue-800 shadow-sm">
                          <h4 className="font-semibold text-blue-600 dark:text-blue-400 flex items-center gap-2 mb-3 text-base">
                            <span className="text-lg">📦</span>
                            Stock Updates
                          </h4>
                          <ul className="space-y-2">
                            {festival.recommendations.stock_updates.map((item, i) => (
                              <li key={i} className="text-sm text-gray-700 dark:text-gray-300 flex items-start gap-2">
                                <span className="text-blue-500 mt-1 flex-shrink-0">•</span>
                                <span className="leading-relaxed">{item}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      {/* Discount Suggestions */}
                      {festival.recommendations.discount_suggestions.length > 0 && (
                        <div className="bg-white/90 dark:bg-gray-900/90 rounded-lg p-5 border border-green-200 dark:border-green-800 shadow-sm">
                          <h4 className="font-semibold text-green-600 dark:text-green-400 flex items-center gap-2 mb-3 text-base">
                            <span className="text-lg">💰</span>
                            Discount Suggestions
                          </h4>
                          <ul className="space-y-2">
                            {festival.recommendations.discount_suggestions.map((item, i) => (
                              <li key={i} className="text-sm text-gray-700 dark:text-gray-300 flex items-start gap-2">
                                <span className="text-green-500 mt-1 flex-shrink-0">•</span>
                                <span className="leading-relaxed">{item}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      {/* Marketing Tips */}
                      {festival.recommendations.marketing_tips.length > 0 && (
                        <div className="bg-white/90 dark:bg-gray-900/90 rounded-lg p-5 border border-purple-200 dark:border-purple-800 shadow-sm">
                          <h4 className="font-semibold text-purple-600 dark:text-purple-400 flex items-center gap-2 mb-3 text-base">
                            <span className="text-lg">📈</span>
                            Marketing Tips
                          </h4>
                          <ul className="space-y-2">
                            {festival.recommendations.marketing_tips.map((item, i) => (
                              <li key={i} className="text-sm text-gray-700 dark:text-gray-300 flex items-start gap-2">
                                <span className="text-purple-500 mt-1 flex-shrink-0">•</span>
                                <span className="leading-relaxed">{item}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
          
          {/* Footer Actions */}
          <div className="px-6 py-6 border-t border-border bg-gray-50/50 dark:bg-gray-900/50">
            <div className="flex flex-col lg:flex-row justify-between items-center gap-4">
              <div className="text-sm text-gray-600 dark:text-gray-400 font-medium text-center lg:text-left">
                💡 Pro Tip: Plan ahead for better sales performance!
              </div>
              <div className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto">
                <Button 
                  onClick={handleGoToChat}
                  disabled={!isBackendConnected || upcomingFestivals.length === 0}
                  variant="outline" 
                  className="w-full sm:w-auto px-6 py-2 border-primary text-primary hover:bg-primary hover:text-primary-foreground font-semibold"
                >
                  <MessageCircle className="h-4 w-4 mr-2" />
                  Go to Chat
                </Button>
                <Button 
                  variant="outline" 
                  onClick={handleRemindLater}
                  className="w-full sm:w-auto px-6 py-2 font-semibold"
                >
                  Remind Later
                </Button>
                <Button 
                  onClick={handleGotIt}
                  className="w-full sm:w-auto bg-orange-600 hover:bg-orange-700 px-6 py-2 font-semibold text-white"
                >
                  Got It! 🎯
                </Button>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Dashboard;
