"""
Quick setup script for Grok alignment.
Helps users configure their API key and test the connection.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def setup_grok_api():
    """Interactive setup for Grok API."""
    
    print("=" * 70)
    print("🚀 GROK ALIGNMENT SETUP")
    print("=" * 70)
    print()
    
    print("This script will help you set up xAI's Grok API for alignment.")
    print()
    
    # Check if API key already exists
    existing_key = os.getenv("XAI_API_KEY")
    if existing_key:
        print("✓ XAI_API_KEY is already set in your environment.")
        print(f"  Current key: {existing_key[:8]}...{existing_key[-4:]}")
        print()
        
        response = input("Do you want to update it? (y/n): ").strip().lower()
        if response != 'y':
            print("\nKeeping existing API key. Setup complete!")
            return test_api_connection(existing_key)
        print()
    
    # Get API key instructions
    print("📋 To get your xAI API key:")
    print("   1. Visit: https://console.x.ai/")
    print("   2. Sign up or log in")
    print("   3. Navigate to 'API Keys'")
    print("   4. Create a new API key")
    print("   5. Copy the key")
    print()
    
    # Prompt for API key
    print("Enter your xAI API key (or press Enter to skip):")
    api_key = input("API Key: ").strip()
    
    if not api_key:
        print("\n⚠️  No API key provided. Skipping setup.")
        print("\nTo set it up later:")
        print("  Linux/Mac:  export XAI_API_KEY='your-key-here'")
        print("  Windows:    set XAI_API_KEY=your-key-here")
        print("  PowerShell: $env:XAI_API_KEY='your-key-here'")
        return False
    
    # Set environment variable for current session
    os.environ["XAI_API_KEY"] = api_key
    print("\n✓ API key set for current session!")
    print()
    
    # Show how to make it permanent
    print("💡 To make this permanent:")
    print()
    
    if sys.platform == "win32":
        print("Windows (Command Prompt):")
        print(f'  setx XAI_API_KEY "{api_key}"')
        print()
        print("Windows (PowerShell):")
        print(f'  [System.Environment]::SetEnvironmentVariable("XAI_API_KEY", "{api_key}", "User")')
    else:
        shell = os.getenv("SHELL", "bash")
        if "zsh" in shell:
            config_file = "~/.zshrc"
        elif "bash" in shell:
            config_file = "~/.bashrc"
        else:
            config_file = "~/.profile"
        
        print(f"Linux/Mac (add to {config_file}):")
        print(f'  export XAI_API_KEY="{api_key}"')
        print()
        print("Then reload your shell:")
        print(f"  source {config_file}")
    
    print()
    
    # Test the connection
    return test_api_connection(api_key)


def test_api_connection(api_key: str) -> bool:
    """Test the API connection with a simple request."""
    
    print("=" * 70)
    print("🔌 TESTING API CONNECTION")
    print("=" * 70)
    print()
    
    try:
        from openai import OpenAI
        
        print("Sending test request to Grok API...")
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )
        
        # Simple test request
        response = client.chat.completions.create(
            model="grok-2-1212",
            messages=[
                {"role": "user", "content": "Say 'Connection successful!' if you can read this."}
            ],
            max_tokens=20,
            temperature=0
        )
        
        message = response.choices[0].message.content
        
        print(f"✅ Connection successful!")
        print(f"   Grok responded: {message}")
        print()
        print("=" * 70)
        print("🎉 SETUP COMPLETE!")
        print("=" * 70)
        print()
        print("You're ready to use Grok alignment!")
        print()
        print("Next steps:")
        print("  1. Run demo:        python demo_grok_alignment.py")
        print("  2. Run comparison:  python compare_alignment_methods.py")
        print("  3. Read guide:      See GROK_ALIGNMENT_GUIDE.md")
        print()
        
        return True
        
    except ImportError:
        print("❌ Error: OpenAI library not installed")
        print("\nInstall it with:")
        print("  pip install openai")
        return False
    
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("  • Check your API key is correct")
        print("  • Ensure you have internet connection")
        print("  • Verify your xAI account is active")
        print("  • Check xAI status: https://status.x.ai/")
        return False


def main():
    """Main setup flow."""
    try:
        success = setup_grok_api()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user.")
        sys.exit(1)


if __name__ == "__main__":
    main()

