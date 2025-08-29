#!/usr/bin/env python3
"""
Test script for voice input functionality
This script tests the WebSocket connection and voice message handling
"""

import asyncio
import websockets
import json
import time

async def test_voice_input():
    """Test voice input functionality via WebSocket"""
    
    uri = "ws://localhost:8765"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket server")
            
            # Wait for welcome message
            welcome_msg = await websocket.recv()
            welcome_data = json.loads(welcome_msg)
            print(f"📨 Welcome message: {welcome_data.get('message', 'No message')}")
            
            # Test voice message
            voice_message = {
                "type": "voice_message",
                "message": "Hello, this is a test voice message",
                "client_agent": "test-script"
            }
            
            print("🎤 Sending voice message...")
            await websocket.send(json.dumps(voice_message))
            
            # Wait for response
            response = await websocket.recv()
            response_data = json.loads(response)
            
            if response_data.get('type') == 'voice_message_response':
                print(f"🤖 AI Response: {response_data.get('message', 'No response')}")
                print(f"⏱️ Response time: {response_data.get('response_time_ms', 0)}ms")
                print("✅ Voice message test successful!")
            else:
                print(f"❌ Unexpected response type: {response_data.get('type')}")
                print(f"Response: {response_data}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_regular_message():
    """Test regular text message functionality"""
    
    uri = "ws://localhost:8765"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("\n📝 Testing regular text message...")
            
            # Wait for welcome message
            await websocket.recv()
            
            # Send regular message
            text_message = {
                "type": "message",
                "message": "This is a regular text message test",
                "client_agent": "test-script"
            }
            
            await websocket.send(json.dumps(text_message))
            
            # Wait for response
            response = await websocket.recv()
            response_data = json.loads(response)
            
            if response_data.get('type') == 'assistant':
                print(f"🤖 AI Response: {response_data.get('message', 'No response')}")
                print(f"⏱️ Response time: {response_data.get('response_time_ms', 0)}ms")
                print("✅ Regular message test successful!")
            else:
                print(f"❌ Unexpected response type: {response_data.get('type')}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    """Run all tests"""
    print("🧪 Testing AI Voice Bot Voice Input Functionality")
    print("=" * 50)
    
    # Test voice message
    await test_voice_input()
    
    # Test regular message
    await test_regular_message()
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
