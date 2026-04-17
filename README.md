# Dont Touch The Button

## Description
This is a rhythm-based game where the player must protect a central button from incoming arrows.

## Gameplay
- Arrows come from 4 directions (Up, Down, Left, Right)
- Player uses arrow keys to move a shield
- Goal: block arrows before they hit the button

## Controls
- ↑ ↓ ← → : Move shield

## Features
- Normal notes (block to gain score)
- Hold notes (hold position to succeed)
- Fake notes (DO NOT block)
- Increasing difficulty over time

## System Design
The game is built using Object-Oriented Programming:
- Game class: controls main loop and states
- Note class: represents each arrow
- Spawner: controls rhythm and spawning
- ScoreManager: handles scoring
- HitJudge: handles collision logic

## Finite State Machine
Game states:
- MENU
- PLAYING
- GAME_OVER

Transitions:
- SPACE → start game
- Button hit → game over
- R → restart
- ESC → back to menu

