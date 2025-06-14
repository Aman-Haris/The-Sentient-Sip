import pygame
from pygame._sdl2 import Window
from llm import invoke_model
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

# Initialize Pygame with larger window
pygame.init()
screen_width, screen_height = 1500, 750  # Increased window size
screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
Window.from_display_module().maximize()
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

# Chat system constants
MAX_VISIBLE_MESSAGES = 20  # Increased message history
LINE_HEIGHT = 30
TEXTBOX_HEIGHT = 500  # Larger text box
TEXTBOX_WIDTH = screen_width - 100
SCROLL_SPEED = 3  # Lines to scroll at once

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
desired_width = 700
desired_height = 700
rita = pygame.transform.scale(load_asset("assets/rita.png"), (desired_width, desired_height))
font = pygame.font.Font("assets/pixel_font.ttf", 24) if os.path.exists("assets/pixel_font.ttf") else pygame.font.SysFont("Arial", 24)
title_font = pygame.font.Font("assets/pixel_font.ttf", 48) if os.path.exists("assets/pixel_font.ttf") else pygame.font.SysFont("Arial", 48)

# Game states
STATE_START = 0
STATE_INFO = 1
STATE_CHAT = 2
game_state = STATE_START

# UI Elements
rita_rect = pygame.Rect(screen_width//2 - rita.get_width()//2, screen_height//2 - rita.get_height()//2, rita.get_width(), rita.get_height())
start_button = pygame.Rect(screen_width//2 - 150, screen_height//2, 300, 80)
info_button = pygame.Rect(screen_width//2 - 150, screen_height//2 + 100, 300, 80)
back_button = pygame.Rect(50, 50, 200, 60)
voice_button = pygame.Rect(screen_width - 220, 50, 170, 40)

# Chat system
full_history = []
chat_lines = []
scroll_offset = 0
input_text = ""
typing_progress = 0
current_typing_text = ""
is_typing = False
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
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    
    if current_line:
        lines.append(' '.join(current_line))
    
    surfaces = []
    for line in lines:
        surfaces.append(font.render(line, True, color))
    return surfaces

def update_chat_display():
    global chat_lines, scroll_offset
    
    chat_lines = []
    y_offset = 0
    
    for msg in full_history[-MAX_VISIBLE_MESSAGES:]:
        speaker = "You" if msg["role"] == "user" else "Rita"
        speaker_color = BLUE if speaker == "You" else RED
        
        # Add speaker tag
        speaker_surface = font.render(f"{speaker}: ", True, speaker_color)
        chat_lines.append((speaker_surface, y_offset))
        y_offset += LINE_HEIGHT
        
        # Add message text
        wrapped_surfaces = render_text_with_wrap(
            msg["content"], font, BLACK, 
            TEXTBOX_WIDTH - 50 - speaker_surface.get_width()
        )
        for surface in wrapped_surfaces:
            chat_lines.append((surface, y_offset))
            y_offset += LINE_HEIGHT
        
        # Add space between messages
        y_offset += LINE_HEIGHT // 2
    
    # Auto-scroll to bottom if not manually scrolling
    if scroll_offset + TEXTBOX_HEIGHT >= y_offset - LINE_HEIGHT:
        scroll_offset = max(0, y_offset - TEXTBOX_HEIGHT + 100)

def speak_async(text):
    def _speak():
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                tts = gTTS(text=text, lang="en")
                tts.save(fp.name)
            
            subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", fp.name], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.unlink(fp.name)
        except Exception as e:
            print(f"Voice error: {e}")
    
    thread = threading.Thread(target=_speak)
    thread.daemon = True
    thread.start()

def listen_async():
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

def get_llm_response_async(message, chat_history=None):
    def _get_response():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(invoke_model(message, chat_history))
            llm_response_queue.put(("success", response))
        except Exception as e:
            llm_response_queue.put(("error", f"Error getting response: {e}"))
        finally:
            loop.close()
    
    thread = threading.Thread(target=_get_response)
    thread.daemon = True
    thread.start()

def handle_chat_input(player_message):
    global full_history, scroll_offset, waiting_for_llm
    
    if not player_message.strip():
        return
        
    full_history.append({"role": "user", "content": player_message})
    update_chat_display()
    
    llm_history = full_history.copy()
    waiting_for_llm = True
    get_llm_response_async(player_message, llm_history)

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
    color = RED if active else GRAY
    
    mic_body = pygame.Rect(x + 8, y + 5, 8, 15)
    pygame.draw.rect(screen, color, mic_body, border_radius=4)
    pygame.draw.rect(screen, BLACK, mic_body, 1, border_radius=4)
    
    pygame.draw.line(screen, color, (x + 12, y + 20), (x + 12, y + 25), 2)
    pygame.draw.line(screen, color, (x + 8, y + 25), (x + 16, y + 25), 2)
    
    if active:
        for i in range(1, 4):
            wave_radius = 5 + i * 3
            wave_color = (RED[0], RED[1], RED[2], max(255 - i * 60, 60))
            pygame.draw.circle(screen, RED, (x + 12, y + 12), wave_radius, 1)

def draw_keyboard_icon(x, y):
    keyboard_rect = pygame.Rect(x + 2, y + 8, 20, 12)
    pygame.draw.rect(screen, GRAY, keyboard_rect, border_radius=2)
    pygame.draw.rect(screen, BLACK, keyboard_rect, 1, border_radius=2)
    
    for row in range(2):
        for col in range(4):
            key_x = x + 4 + col * 4
            key_y = y + 10 + row * 4
            key_rect = pygame.Rect(key_x, key_y, 3, 3)
            pygame.draw.rect(screen, WHITE, key_rect)
            pygame.draw.rect(screen, BLACK, key_rect, 1)

def draw_listening_animation(x, y):
    global mic_animation_frames
    
    if not listening:
        return
    
    mic_animation_frames += 1
    
    pulse_size = int(10 + 5 * abs(math.sin(mic_animation_frames * 0.1)))
    pulse_surface = pygame.Surface((pulse_size * 2, pulse_size * 2), pygame.SRCALPHA)
    pygame.draw.circle(pulse_surface, (255, 0, 0, 100), (pulse_size, pulse_size), pulse_size)
    screen.blit(pulse_surface, (x - pulse_size + 12, y - pulse_size + 12))
    
    listening_text = font.render("LISTENING...", True, RED)
    screen.blit(listening_text, (x - 50, y + 35))

# Main game loop
running = True
while running:
    dt = clock.tick(60) / 1000.0  # Increased to 60 FPS for smoother scrolling

    # Check for voice input
    if not voice_input_queue.empty():
        status, message = voice_input_queue.get()
        if status == "success":
            handle_chat_input(message)
        else:
            full_history.append({"role": "system", "content": message})
            update_chat_display()

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
            
            full_history.append({"role": "assistant", "content": response})
            update_chat_display()
        else:
            error_msg = "Sorry, I'm having trouble responding right now."
            full_history.append({"role": "assistant", "content": error_msg})
            update_chat_display()
        
        is_typing = False

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if game_state == STATE_START:
                if start_button.collidepoint(event.pos):
                    game_state = STATE_CHAT
                    initial_message = "Welcome to The Sentient Sip! How can I help you today?"
                    full_history = [{"role": "assistant", "content": initial_message}]
                    update_chat_display()
                elif info_button.collidepoint(event.pos):
                    game_state = STATE_INFO
                    
            elif game_state == STATE_INFO and back_button.collidepoint(event.pos):
                game_state = STATE_START
                
            elif game_state == STATE_CHAT and voice_button.collidepoint(event.pos):
                voice_mode = not voice_mode
                
        elif event.type == pygame.MOUSEWHEEL:
            if game_state == STATE_CHAT:
                scroll_offset = max(0, scroll_offset - event.y * SCROLL_SPEED * LINE_HEIGHT)
                
        elif event.type == pygame.KEYDOWN and game_state == STATE_CHAT:
            if voice_mode and event.key == pygame.K_SPACE and not listening:
                listen_async()
            elif not voice_mode:
                if event.key == pygame.K_RETURN and not waiting_for_llm:
                    handle_chat_input(input_text)
                    input_text = ""
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.key == pygame.K_UP:
                    scroll_offset = max(0, scroll_offset - SCROLL_SPEED * LINE_HEIGHT)
                elif event.key == pygame.K_DOWN:
                    max_offset = max(0, len(chat_lines) * LINE_HEIGHT - TEXTBOX_HEIGHT + 100)
                    scroll_offset = min(max_offset, scroll_offset + SCROLL_SPEED * LINE_HEIGHT)
                elif event.unicode and event.unicode.isprintable():
                    input_text += event.unicode

    # Update typing animation
    if game_state == STATE_CHAT and is_typing and typing_progress < len(current_typing_text):
        typing_progress += 30 * dt
        update_chat_display()

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
            "- Mouse wheel or Up/Down arrows to scroll", "",
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
        
        if voice_mode:
            draw_microphone_icon(voice_button.x + 10, voice_button.y + 10, listening)
        else:
            draw_keyboard_icon(voice_button.x + 10, voice_button.y + 10)
        
        mode_text = "VOICE" if voice_mode else "TEXT"
        screen.blit(font.render(mode_text, True, BLACK), 
                   (voice_button.x + 40, voice_button.y + 10))
        
        if voice_mode:
            glow = pygame.Surface((voice_button.width+6, voice_button.height+6), pygame.SRCALPHA)
            pygame.draw.rect(glow, YELLOW_GLOW, (0, 0, voice_button.width+6, voice_button.height+6), border_radius=23)
            screen.blit(glow, (voice_button.x-3, voice_button.y-3))
        
        if voice_mode:
            draw_listening_animation(screen_width - 270, 55)

        # Text box
        textbox_rect = pygame.Rect(50, screen_height - TEXTBOX_HEIGHT - 50, TEXTBOX_WIDTH, TEXTBOX_HEIGHT)
        pygame.draw.rect(screen, BLACK, textbox_rect)
        pygame.draw.rect(screen, WHITE, (textbox_rect.x+2, textbox_rect.y+2, textbox_rect.width-4, textbox_rect.height-4))

        # Draw chat lines with scrolling
        screen.set_clip(textbox_rect)
        y_pos = textbox_rect.y + 10 - scroll_offset
        for surface, y_offset in chat_lines:
            if y_pos + y_offset < textbox_rect.y + textbox_rect.height - 20:
                screen.blit(surface, (textbox_rect.x + 20, y_pos + y_offset))
        screen.set_clip(None)

        # Scroll bar
        if len(chat_lines) * LINE_HEIGHT > TEXTBOX_HEIGHT:
            scrollbar_height = min(TEXTBOX_HEIGHT, 
                                 (TEXTBOX_HEIGHT ** 2) / (len(chat_lines) * LINE_HEIGHT))
            scrollbar_pos = (scroll_offset / (len(chat_lines) * LINE_HEIGHT)) * TEXTBOX_HEIGHT
            pygame.draw.rect(screen, GRAY, (
                textbox_rect.right - 10,
                textbox_rect.y + scrollbar_pos,
                8,
                scrollbar_height
            ))

        # Input box
        input_rect = pygame.Rect(textbox_rect.x + 20, textbox_rect.y + textbox_rect.height + 10, textbox_rect.width - 40, 40)
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
        if len(full_history) > 1:
            hint_text += " | Mouse wheel or Up/Down to scroll"
        screen.blit(font.render(hint_text, True, GRAY), (textbox_rect.x + 20, textbox_rect.y - 30))

    pygame.display.flip()

pygame.quit()