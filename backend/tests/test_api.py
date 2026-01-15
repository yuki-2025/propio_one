"""
测试 FastAPI LangChain Agent 服务
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查端点"""
    print("🔍 测试健康检查...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_chat():
    """测试聊天端点"""
    print("💬 测试聊天端点...")
    payload = {
        "message": "What is the weather outside?",
        "user_id": "1"
    }
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_chat_stream():
    """测试流式聊天端点"""
    print("🌊 测试流式聊天...")
    payload = {
        "message": "Tell me about the weather in a fun way",
        "user_id": "1"
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/stream",
        json=payload,
        headers={"Content-Type": "application/json"},
        stream=True
    )
    
    print(f"状态码: {response.status_code}")
    print("流式响应:")
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith('data: '):
                content = decoded_line[6:]  # 移除 'data: ' 前缀
                print(f"  {content}")
    print()

def test_conversation_continuity():
    """测试对话连续性"""
    print("🔄 测试对话连续性...")
    
    # 第一条消息
    payload1 = {
        "message": "What is the weather outside?",
        "user_id": "1"
    }
    response1 = requests.post(f"{BASE_URL}/chat", json=payload1)
    thread_id = response1.json()["thread_id"]
    print(f"第一条消息 - Thread ID: {thread_id}")
    print(f"响应: {response1.json()['punny_response'][:100]}...")
    
    # 第二条消息（使用相同的 thread_id）
    payload2 = {
        "message": "Thank you!",
        "user_id": "1",
        "thread_id": thread_id
    }
    response2 = requests.post(f"{BASE_URL}/chat", json=payload2)
    print(f"\n第二条消息 - Thread ID: {response2.json()['thread_id']}")
    print(f"响应: {response2.json()['punny_response'][:100]}...")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("FastAPI LangChain Agent 测试")
    print("=" * 60)
    print()
    
    try:
        # 1. 健康检查
        test_health()
        
        # 2. 基本聊天
        test_chat()
        
        # 3. 流式聊天
        test_chat_stream()
        
        # 4. 对话连续性
        test_conversation_continuity()
        
        print("✅ 所有测试完成！")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器。请确保 FastAPI 服务正在运行：")
        print("   uv run uvicorn api:app --host 0.0.0.0 --port 8000 --reload")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
