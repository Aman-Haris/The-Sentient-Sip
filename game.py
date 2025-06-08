import pygame
from llm import llm
import asyncio
import os
import time
import math
import speech_recognition as sr
from gtts import gTTS
import tempfile
import subprocess
import threading
from queue import Queue

# Initialize Pygame
pygame.init()
screen_width, screen_height = 1280, 720
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("The Sentient Sip")
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
RED = (255, 0, 0)
PINK = (255, 200, 200)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW_GLOW = (255, 255, 0, 30)

# Voice mode
voice_mode = False
listening = False
mic_animation_frames = 0
mic_animation_active = False
voice_input_queue = Queue()
llm_response_queue = Queue()

# Load assets
def load_asset(path, fallback_size=None, fallback_color=(255, 0, 255)):
    try:
        return pygame.image.load(path)
    except:
        print(f"Could not load {path}, using fallback")
        if fallback_size:
            surface = pygame.Surface(fallback_size)
            surface.fill(fallback_color)
            return surface
        return None

bg = load_asset("assets/cafe_background.png", (screen_width, screen_height), (200, 200, 200))
rita = load_asset("assets/rita.png", (200, 400), (255, 0, 0))
font = pygame.font.Font("assets/pixel_font.ttf", 24) if os.path.exists("assets/pixel_font.ttf") else pygame.font.SysFont("Arial", 24)
title_font = pygame.font.Font("assets/pixel_font.ttf", 48) if os.path.exists("assets/pixel_font.ttf") else pygame.font.SysFont("Arial", 48)

# Game states
STATE_START = 0
STATE_INFO = 1
STATE_CHAT = 2
game_state = STATE_START

# UI Elements
rita_rect = pygame.Rect(screen_width//2 - 100, screen_height//2 - 100, 200, 400)
start_button = pygame.Rect(screen_width//2 - 150, screen_height//2, 300, 80)
info_button = pygame.Rect(screen_width//2 - 150, screen_height//2 + 100, 300, 80)
back_button = pygame.Rect(50, 50, 200, 60)
voice_button = pygame.Rect(screen_width - 220, 50, 170, 40)

# Chat system
history = []
full_history = []
input_text = ""
typing_progress = 0
current_typing_text = ""
is_typing = False
history_offset = 0
waiting_for_llm = False

def render_text_with_wrap(text, font, color, max_width):
    words = text.split(' ')
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        if font.size(test_line)[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:  # Only append if current_line is not empty
                lines.append(' '.join(current_line))
                current_line = [word]
            else:  # Handle very long words
                lines.append(word)
                current_line = []
    
    if current_line:  # Don't forget the last line
        lines.append(' '.join(current_line))
    
    return [font.render(line, True, color) for line in lines]

def speak_async(text):
    """Non-blocking TTS function using threading"""
    def _speak():
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                tts = gTTS(text=text, lang="en")
                tts.save(fp.name)
            
            # Use subprocess to avoid playsound issues
            subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", fp.name], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.unlink(fp.name)
        except Exception as e:
            print(f"Voice error: {e}")
    
    thread = threading.Thread(target=_speak)
    thread.daemon = True
    thread.start()

def listen_async():
    """Non-blocking speech recognition using threading"""
    def _listen():
        global mic_animation_active, listening
        r = sr.Recognizer()
        mic_animation_active = True
        listening = True
        
        try:
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=1)
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
                result = r.recognize_google(audio)
                voice_input_queue.put(("success", result))
        except sr.UnknownValueError:
            voice_input_queue.put(("error", "[Could not understand audio]"))
        except sr.RequestError as e:
            voice_input_queue.put(("error", f"[Speech service error: {e}]"))
        except Exception as e:
            voice_input_queue.put(("error", f"[Microphone error: {e}]"))
        finally:
            mic_animation_active = False
            listening = False
    
    thread = threading.Thread(target=_listen)
    thread.daemon = True
    thread.start()

def get_llm_response_async(message):
    """Non-blocking LLM response using threading"""
    def _get_response():
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(llm(message))
            llm_response_queue.put(("success", response))
        except Exception as e:
            llm_response_queue.put(("error", f"Error getting response: {e}"))
        finally:
            loop.close()
    
    thread = threading.Thread(target=_get_response)
    thread.daemon = True
    thread.start()

def handle_chat_input(player_message):
    global history, full_history, current_typing_text, typing_progress, is_typing, waiting_for_llm
    
    if not player_message.strip():
        return
        
    # Add player message to history
    history.append(("You", player_message))
    full_history.append(("You", player_message))
    
    # Start waiting for LLM response
    waiting_for_llm = True
    get_llm_response_async(player_message)
    
    # Keep only last 2 exchanges in visible history
    if len(history) > 4:  # 2 exchanges = 4 messages
        history = history[-4:]

def draw_button(rect, text, color, hover_color):
    mouse_pos = pygame.mouse.get_pos()
    current_color = hover_color if rect.collidepoint(mouse_pos) else color
    
    pygame.draw.rect(screen, current_color, rect, border_radius=10)
    pygame.draw.rect(screen, BLACK, rect, 2, border_radius=10)
    
    text_surface = font.render(text, True, BLACK)
    text_rect = text_surface.get_rect(center=rect.center)
    screen.blit(text_surface, text_rect)
    return rect.collidepoint(mouse_pos)

def draw_microphone_icon(x, y, active=False):
    """Draw a simple microphone icon using basic shapes"""
    color = RED if active else GRAY
    
    # Microphone body (rectangle)
    mic_body = pygame.Rect(x + 8, y + 5, 8, 15)
    pygame.draw.rect(screen, color, mic_body, border_radius=4)
    pygame.draw.rect(screen, BLACK, mic_body, 1, border_radius=4)
    
    # Microphone base (line)
    pygame.draw.line(screen, color, (x + 12, y + 20), (x + 12, y + 25), 2)
    pygame.draw.line(screen, color, (x + 8, y + 25), (x + 16, y + 25), 2)
    
    # Draw sound waves if active
    if active:
        for i in range(1, 4):
            wave_radius = 5 + i * 3
            # Draw arc-like lines to simulate sound waves
            for angle in range(-30, 31, 10):
                start_x = x + 25 + int(wave_radius * 0.8)
                start_y = y + 12
                end_x = start_x + int(wave_radius * 0.2)
                end_y = start_y
                
                # Simple wave effect
                wave_color = (RED[0], RED[1], RED[2], max(255 - i * 60, 60))
                pygame.draw.circle(screen, RED, (x + 12, y + 12), wave_radius, 1)

def draw_keyboard_icon(x, y):
    """Draw a simple keyboard icon using rectangles"""
    # Keyboard outline
    keyboard_rect = pygame.Rect(x + 2, y + 8, 20, 12)
    pygame.draw.rect(screen, GRAY, keyboard_rect, border_radius=2)
    pygame.draw.rect(screen, BLACK, keyboard_rect, 1, border_radius=2)
    
    # Keys
    for row in range(2):
        for col in range(4):
            key_x = x + 4 + col * 4
            key_y = y + 10 + row * 4
            key_rect = pygame.Rect(key_x, key_y, 3, 3)
            pygame.draw.rect(screen, WHITE, key_rect)
            pygame.draw.rect(screen, BLACK, key_rect, 1)

def draw_listening_animation(x, y):
    """Draw animated listening indicator"""
    global mic_animation_frames
    
    if not listening:
        return
    
    mic_animation_frames += 1
    
    # Pulsing circle
    pulse_size = int(10 + 5 * abs(math.sin(mic_animation_frames * 0.1)))
    pulse_surface = pygame.Surface((pulse_size * 2, pulse_size * 2), pygame.SRCALPHA)
    pygame.draw.circle(pulse_surface, (255, 0, 0, 100), (pulse_size, pulse_size), pulse_size)
    screen.blit(pulse_surface, (x - pulse_size + 12, y - pulse_size + 12))
    
    # "LISTENING..." text
    listening_text = font.render("LISTENING...", True, RED)
    screen.blit(listening_text, (x - 50, y + 35))

# Main game loop
running = True
while running:
    dt = clock.tick(30) / 1000.0

    # Check for voice input
    if not voice_input_queue.empty():
        status, message = voice_input_queue.get()
        if status == "success":
            handle_chat_input(message)
        else:
            # Handle voice recognition errors by showing them in chat
            history.append(("System", message))
            full_history.append(("System", message))

    # Check for LLM response
    if not llm_response_queue.empty():
        status, response = llm_response_queue.get()
        waiting_for_llm = False
        
        if status == "success":
            current_typing_text = response
            typing_progress = 0
            is_typing = True
            
            if voice_mode:
                speak_async(response)
            
            history.append(("Rita", response))
            full_history.append(("Rita", response))
        else:
            # Handle LLM errors
            error_msg = "Sorry, I'm having trouble responding right now."
            history.append(("Rita", error_msg))
            full_history.append(("Rita", error_msg))
        
        is_typing = False

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if game_state == STATE_START:
                if start_button.collidepoint(event.pos):
                    game_state = STATE_CHAT
                    history = [("Rita", "Welcome to The Sentient Sip! How can I help you today?")]
                    full_history = history.copy()
                elif info_button.collidepoint(event.pos):
                    game_state = STATE_INFO
                    
            elif game_state == STATE_INFO and back_button.collidepoint(event.pos):
                game_state = STATE_START
                
            elif game_state == STATE_CHAT and voice_button.collidepoint(event.pos):
                voice_mode = not voice_mode
                
        elif event.type == pygame.KEYDOWN and game_state == STATE_CHAT:
            if voice_mode and event.key == pygame.K_SPACE and not listening:
                # Use SPACE to trigger voice input in voice mode
                listen_async()
            elif not voice_mode:
                if event.key == pygame.K_RETURN and not waiting_for_llm:
                    handle_chat_input(input_text)
                    input_text = ""
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.key == pygame.K_PAGEUP and len(full_history) > 4:
                    history_offset = min(history_offset + 2, len(full_history) - 4)
                    start_idx = max(0, len(full_history) - 4 - history_offset)
                    end_idx = len(full_history) - history_offset
                    history = full_history[start_idx:end_idx]
                elif event.key == pygame.K_PAGEDOWN and history_offset > 0:
                    history_offset = max(history_offset - 2, 0)
                    if history_offset == 0:
                        history = full_history[-4:] if len(full_history) > 4 else full_history
                    else:
                        start_idx = max(0, len(full_history) - 4 - history_offset)
                        end_idx = len(full_history) - history_offset
                        history = full_history[start_idx:end_idx]
                elif event.unicode and event.unicode.isprintable():
                    input_text += event.unicode

    # Update animations
    if game_state == STATE_CHAT and is_typing and typing_progress < len(current_typing_text):
        typing_progress += 30 * dt

    # Drawing
    screen.fill(BLACK)
    
    if game_state == STATE_START:
        screen.blit(bg, (0, 0))
        title_surface = title_font.render("The Sentient Sip", True, WHITE)
        title_shadow = title_font.render("The Sentient Sip", True, BLACK)
        screen.blit(title_shadow, (screen_width//2 - title_surface.get_width()//2 + 5, screen_height//4 + 5))
        screen.blit(title_surface, (screen_width//2 - title_surface.get_width()//2, screen_height//4))
        
        start_hover = draw_button(start_button, "START", PINK, WHITE)
        info_hover = draw_button(info_button, "INFO", PINK, WHITE)
        screen.blit(pygame.transform.scale(rita, (100, 200)), (screen_width - 150, screen_height - 250))
        
    elif game_state == STATE_INFO:
        screen.fill((50, 50, 70))
        draw_button(back_button, "BACK", PINK, WHITE)
        
        info_lines = [
            "THE SENTIENT SIP", "", "A conversational AI experience",
            "where you chat with Rita,", "your digital waitress at",
            "a futuristic café.", "", "Controls:",
            "TEXT MODE:", "- Type and press ENTER to chat",
            "VOICE MODE:", "- Press SPACE to start speaking",
            "- Page Up/Down to browse history", "",
            "Created with Mistral AI and Pygame"
        ]
        
        y_offset = 120
        for line in info_lines:
            text_surface = font.render(line, True, WHITE)
            screen.blit(text_surface, (screen_width//2 - text_surface.get_width()//2, y_offset))
            y_offset += 35
        
    elif game_state == STATE_CHAT:
        screen.blit(bg, (0, 0))
        
        # Draw Rita
        mouse_pos = pygame.mouse.get_pos()
        if rita_rect.collidepoint(mouse_pos):
            highlight = pygame.Surface((rita_rect.width+10, rita_rect.height+10), pygame.SRCALPHA)
            highlight.fill((255, 255, 255, 50))
            screen.blit(highlight, (rita_rect.x-5, rita_rect.y-5))
        screen.blit(rita, (rita_rect.x, rita_rect.y))

        # Voice toggle button
        voice_color = GREEN if voice_mode else PINK
        pygame.draw.rect(screen, voice_color, voice_button, border_radius=20)
        pygame.draw.rect(screen, BLACK, voice_button, 2, border_radius=20)
        
        # Draw mode-specific icon and text
        if voice_mode:
            draw_microphone_icon(voice_button.x + 10, voice_button.y + 10, listening)
        else:
            draw_keyboard_icon(voice_button.x + 10, voice_button.y + 10)
        
        mode_text = "VOICE" if voice_mode else "TEXT"
        screen.blit(font.render(mode_text, True, BLACK), 
                   (voice_button.x + 40, voice_button.y + 10))
        
        # Glow effect for voice mode
        if voice_mode:
            glow = pygame.Surface((voice_button.width+6, voice_button.height+6), pygame.SRCALPHA)
            pygame.draw.rect(glow, YELLOW_GLOW, (0, 0, voice_button.width+6, voice_button.height+6), border_radius=23)
            screen.blit(glow, (voice_button.x-3, voice_button.y-3))
        
        # Listening animation
        if voice_mode:
            draw_listening_animation(screen_width - 270, 55)

        # Text box
        textbox_rect = pygame.Rect(50, screen_height - 250, screen_width - 100, 200)
        pygame.draw.rect(screen, BLACK, textbox_rect)
        pygame.draw.rect(screen, WHITE, (textbox_rect.x+2, textbox_rect.y+2, textbox_rect.width-4, textbox_rect.height-4))

        # Messages
        y_offset = textbox_rect.y + 20
        
        for speaker, text in history:
            # Color code speakers
            speaker_color = RED if speaker == "Rita" else BLUE if speaker == "You" else GRAY
            name_surface = font.render(f"{speaker}:", True, speaker_color)
            screen.blit(name_surface, (textbox_rect.x + 20, y_offset))
            
            for line in render_text_with_wrap(text, font, BLACK, textbox_rect.width - 40 - name_surface.get_width()):
                screen.blit(line, (textbox_rect.x + 30 + name_surface.get_width(), y_offset))
                y_offset += line.get_height() + 5
            y_offset += 10  # Extra space between messages

        # Input box (only show in text mode)
        if not voice_mode:
            input_rect = pygame.Rect(textbox_rect.x + 20, textbox_rect.y + textbox_rect.height - 50, textbox_rect.width - 40, 40)
            pygame.draw.rect(screen, WHITE, input_rect)
            pygame.draw.rect(screen, BLACK, input_rect, 2)
            
            input_surface = font.render(f"> {input_text}", True, BLACK)
            screen.blit(input_surface, (input_rect.x + 10, input_rect.y + 10))
            
            # Cursor
            if pygame.time.get_ticks() % 1000 < 500:
                cursor_x = input_rect.x + 20 + font.size(f"> {input_text}")[0]
                pygame.draw.rect(screen, BLACK, (cursor_x, input_rect.y + 10, 2, 20))

        # Status indicators
        status_y = textbox_rect.y - 60
        if waiting_for_llm:
            status_surface = font.render("Rita is thinking...", True, GRAY)
            screen.blit(status_surface, (textbox_rect.x + 20, status_y))
        
        # Hints
        hint_text = "Press SPACE to talk" if voice_mode else "Type and press ENTER"
        if len(full_history) > 4:
            hint_text += " | Page Up/Down: History"
        screen.blit(font.render(hint_text, True, GRAY), (textbox_rect.x + 20, textbox_rect.y - 30))

        # History indicator
        if len(full_history) > 4:
            current_page = history_offset // 2 + 1
            total_pages = (len(full_history) - 1) // 2
            screen.blit(font.render(f"Page {current_page}/{total_pages}", True, GRAY),
                       (textbox_rect.x + textbox_rect.width - 150, textbox_rect.y - 30))

    pygame.display.flip()

pygame.quit()