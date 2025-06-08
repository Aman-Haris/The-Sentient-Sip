import pygame
from llm import llm
from prompt import get_system_prompt
import asyncio
import os

# Initialize Pygame
pygame.init()
screen_width, screen_height = 1280, 720  # 16:9 aspect ratio
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("The Sentient Sip")
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
RED = (255, 0, 0)
PINK = (255, 200, 200)

# Load assets with error handling
def load_asset(path, fallback_size=None, fallback_color=(255, 0, 255)):
    try:
        asset = pygame.image.load(path)
        return asset
    except:
        print(f"Could not load {path}, using fallback")
        if fallback_size:
            surface = pygame.Surface(fallback_size)
            surface.fill(fallback_color)
            return surface
        return None

# Load assets
bg = load_asset("assets/cafe_background.png", (screen_width, screen_height), (200, 200, 200))
rita = load_asset("assets/rita.png", (200, 400), (255, 0, 0))
font = pygame.font.Font("assets/pixel_font.ttf", 24) if os.path.exists("assets/pixel_font.ttf") else pygame.font.SysFont("Arial", 24)
title_font = pygame.font.Font("assets/pixel_font.ttf", 48) if os.path.exists("assets/pixel_font.ttf") else pygame.font.SysFont("Arial", 48)

# Game states
STATE_START = 0
STATE_INFO = 1
STATE_CHAT = 2
game_state = STATE_START

# Game elements
rita_rect = pygame.Rect(screen_width//2 - 100, screen_height//2 - 100, 200, 400)
start_button = pygame.Rect(screen_width//2 - 150, screen_height//2, 300, 80)
info_button = pygame.Rect(screen_width//2 - 150, screen_height//2 + 100, 300, 80)
back_button = pygame.Rect(50, 50, 200, 60)

# Chat system
history = []
full_history = []
input_text = ""
typing_progress = 0
current_typing_text = ""
is_typing = False
history_offset = 0

def render_text_with_wrap(text, font, color, max_width):
    """Render text with word wrapping"""
    words = text.split(' ')
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        if font.size(test_line)[0] <= max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    lines.append(' '.join(current_line))
    
    return [font.render(line, True, color) for line in lines]

async def handle_chat():
    """Process player input and get Rita's response"""
    global input_text, history, full_history, current_typing_text, typing_progress, is_typing
    
    if not input_text.strip():
        return
        
    is_typing = True
    player_message = input_text
    input_text = ""
    
    # Add player message to history
    history.append(("You", player_message))
    full_history.append(("You", player_message))
    
    # Get Rita's response
    response = await llm(player_message)
    current_typing_text = response
    typing_progress = 0
    
    # Add to history after typing completes
    is_typing = False
    history.append(("Rita", response))
    full_history.append(("Rita", response))
    
    # Keep only last 2 messages in main view
    if len(history) > 2:
        history = history[-2:]

def draw_button(rect, text, color, hover_color):
    mouse_pos = pygame.mouse.get_pos()
    current_color = hover_color if rect.collidepoint(mouse_pos) else color
    
    pygame.draw.rect(screen, current_color, rect, border_radius=10)
    pygame.draw.rect(screen, BLACK, rect, 2, border_radius=10)  # Border
    
    text_surface = font.render(text, True, BLACK)
    text_rect = text_surface.get_rect(center=rect.center)
    screen.blit(text_surface, text_rect)
    return rect.collidepoint(mouse_pos)

# Main game loop
running = True
while running:
    dt = clock.tick(30) / 1000.0  # Delta time in seconds

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
                
            elif game_state == STATE_CHAT and rita_rect.collidepoint(event.pos):
                pass  # Handle Rita clicks if needed
                
        elif event.type == pygame.KEYDOWN and game_state == STATE_CHAT and not is_typing:
            if event.key == pygame.K_RETURN:
                asyncio.run(handle_chat())
            elif event.key == pygame.K_BACKSPACE:
                input_text = input_text[:-1]
            elif event.key == pygame.K_PAGEUP and len(full_history) > 2:
                # Scroll history up
                history_offset = min(history_offset + 1, len(full_history) - 2)
                history = full_history[-2 - history_offset : -history_offset if history_offset else None]
            elif event.key == pygame.K_PAGEDOWN and history_offset > 0:
                # Scroll history down
                history_offset = max(history_offset - 1, 0)
                history = full_history[-2 - history_offset : -history_offset if history_offset else None]
            elif event.key not in [pygame.K_RETURN, pygame.K_PAGEUP, pygame.K_PAGEDOWN]:
                input_text += event.unicode

    # Update typing animation
    if game_state == STATE_CHAT and typing_progress < len(current_typing_text):
        typing_progress += 30 * dt  # Adjust typing speed

    # Drawing
    screen.fill(BLACK)  # Clear screen
    
    if game_state == STATE_START:
        # Draw start screen
        screen.blit(bg, (0, 0))
        
        # Title
        title_surface = title_font.render("The Sentient Sip", True, WHITE)
        title_shadow = title_font.render("The Sentient Sip", True, BLACK)
        screen.blit(title_shadow, (screen_width//2 - title_surface.get_width()//2 + 5, screen_height//4 + 5))
        screen.blit(title_surface, (screen_width//2 - title_surface.get_width()//2, screen_height//4))
        
        # Buttons
        start_hover = draw_button(start_button, "START", PINK, WHITE)
        info_hover = draw_button(info_button, "INFO", PINK, WHITE)
        
        # Rita teaser
        rita_teaser = pygame.transform.scale(rita, (100, 200))
        screen.blit(rita_teaser, (screen_width - 150, screen_height - 250))
        
    elif game_state == STATE_INFO:
        # Draw info screen
        screen.fill((50, 50, 70))
        
        # Back button
        draw_button(back_button, "BACK", PINK, WHITE)
        
        # Info text
        info_lines = [
            "THE SENTIENT SIP",
            "",
            "A conversational AI experience",
            "where you chat with Rita,",
            "your digital waitress at",
            "a futuristic café.",
            "",
            "Controls:",
            "- Click Rita to start chatting",
            "- Type your message and press Enter",
            "- Page Up/Down to browse history",
            "",
            "Created with Mistral AI and Pygame"
        ]
        
        y_offset = 150
        for line in info_lines:
            text_surface = font.render(line, True, WHITE)
            screen.blit(text_surface, (screen_width//2 - text_surface.get_width()//2, y_offset))
            y_offset += 40
        
    elif game_state == STATE_CHAT:
        # Draw chat screen
        screen.blit(bg, (0, 0))
        
        # Draw Rita
        mouse_pos = pygame.mouse.get_pos()
        if rita_rect.collidepoint(mouse_pos):
            highlight = pygame.Surface((rita_rect.width+10, rita_rect.height+10))
            highlight.set_alpha(50)
            highlight.fill(WHITE)
            screen.blit(highlight, (rita_rect.x-5, rita_rect.y-5))
        
        screen.blit(rita, (rita_rect.x, rita_rect.y))

        # Draw text box
        textbox_rect = pygame.Rect(50, screen_height - 250, screen_width - 100, 200)
        pygame.draw.rect(screen, BLACK, textbox_rect)
        pygame.draw.rect(screen, WHITE, (textbox_rect.x+2, textbox_rect.y+2, textbox_rect.width-4, textbox_rect.height-4))

        # Render messages with wrapping
        y_offset = textbox_rect.y + 20
        visible_history = history if not is_typing else history[:-1] + [("Rita", current_typing_text[:int(typing_progress)])]
        
        for speaker, text in visible_history:
            # Speaker name
            name_surface = font.render(f"{speaker}:", True, RED)
            screen.blit(name_surface, (textbox_rect.x + 20, y_offset))
            
            # Message text with wrapping
            wrapped_lines = render_text_with_wrap(
                text,
                font,
                BLACK,
                textbox_rect.width - 40 - name_surface.get_width()
            )
            
            for line in wrapped_lines:
                screen.blit(line, (textbox_rect.x + 30 + name_surface.get_width(), y_offset))
                y_offset += line.get_height() + 5

        # Input box
        input_rect = pygame.Rect(textbox_rect.x + 20, textbox_rect.y + textbox_rect.height - 50, textbox_rect.width - 40, 40)
        pygame.draw.rect(screen, WHITE, input_rect)
        pygame.draw.rect(screen, BLACK, input_rect, 2)
        
        input_surface = font.render(f"> {input_text}", True, BLACK)
        screen.blit(input_surface, (input_rect.x + 10, input_rect.y + 10))
        
        # Blinking cursor
        if pygame.time.get_ticks() % 1000 < 500:  # Blink every 500ms
            cursor_x = input_rect.x + 20 + input_surface.get_width()
            pygame.draw.rect(screen, BLACK, (cursor_x, input_rect.y + 10, 8, 25))

        # Input hint
        hint_text = "Type and press ENTER" + (" | Page Up/Down: History" if len(full_history) > 2 else "")
        hint_surface = font.render(hint_text, True, GRAY)
        screen.blit(hint_surface, (input_rect.x, input_rect.y - 30))

        # History navigation
        if len(full_history) > 2:
            history_text = f"History ({history_offset}/{len(full_history)-2})"
            history_surface = font.render(history_text, True, GRAY)
            screen.blit(history_surface, (textbox_rect.x + textbox_rect.width - 200, textbox_rect.y - 30))

    pygame.display.flip()

pygame.quit()