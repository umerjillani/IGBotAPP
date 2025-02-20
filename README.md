# Instagram AI Bot

An AI-powered Instagram bot built with Flask that:
- Responds to DMs
- Replies to comments on posts
- Sends DMs to users who comment

## Prerequisites
- Instagram Business Account (required for `INSTAGRAM_BUSINESS_ID` and `ACCESS_TOKEN`)
- [OpenAI API Key](https://platform.openai.com/api-keys)
- Basic familiarity with command-line tools

---

## Installation Guide

### **1. Install Required Software**
1. **Python 3.8+**:  
   Download and install from [python.org](https://www.python.org/downloads/).  
   Verify installation in **Command Prompt/Terminal**:  
   ```bash
   python --version  # or python3 --version
   ```
2. **Git**:  
   Install from [git-scm.com](https://git-scm.com/downloads). Verify with:  
   ```bash
   git --version
   ```
3. **VS Code (Optional)**:  
   Install from [code.visualstudio.com](https://code.visualstudio.com/).

---

### **2. Clone the Repository**
1. Open **Command Prompt/Terminal**.  
2. Navigate to your desired directory (e.g., `Desktop`):  
   ```bash
   cd Desktop
   ```
3. Clone the repo:  
   ```bash
   git clone https://github.com/yourusername/your-repo.git
   cd your-repo
   ```

---

### **3. Set Up a Virtual Environment**
1. Create a virtual environment:  
   ```bash
   python -m venv venv  # Use python3 if needed
   ```
2. Activate it:  
   - **Windows**:  
     ```bash
     venv\Scripts\activate
     ```
   - **macOS/Linux**:  
     ```bash
     source venv/bin/activate
     ```
   *(Your terminal prompt will show `(venv)` when active.)*

---

### **4. Install Dependencies**
Run this command **inside the activated virtual environment**:  
```bash
pip install -r requirements.txt
```

---

### **5. Configure Environment Variables**
1. Create a `.env` file in the project root:  
   - **Command Prompt/Terminal**:  
     ```bash
     touch .env  # Or use "New File" in VS Code
     ```
2. Add the following variables to `.env`:  
   ```ini
   ACCESS_TOKEN=your_instagram_access_token
   INSTAGRAM_BUSINESS_ID=your_business_id
   VERIFY_TOKEN=your_verification_token
   OPENAI_API_KEY=your_openai_key
   ```
   *(Replace placeholders with your actual credentials.)*

---

### **6. Generate Instagram Access Token**
1. Install Jupyter Notebook (if not in `requirements.txt`):  
   ```bash
   pip install jupyter
   ```
2. Start Jupyter:  
   ```bash
   jupyter notebook
   ```
3. Open `token_generator.ipynb` in your browser.  
4. Follow the notebook instructions to generate `ACCESS_TOKEN`.  
5. **Update the `.env` file** with the new token.

---

### **7. Run the Flask Server**
In the **activated virtual environment**, run:  
```bash
python app.py  # or python3 app.py
```
The bot will start at `http://127.0.0.1:5000/`.

---

### **8. Set Up Webhooks with Ngrok**
1. **Download Ngrok** from [ngrok.com](https://ngrok.com/download) and unzip it.  
   [Download Ngrok](https://ngrok.com/download)
2. Open a **new terminal window** and navigate to the Ngrok directory.  
3. Expose the Flask server:  
   ```bash
   ./ngrok http 5000  # Windows: ngrok.exe http 5000
   ```
4. Copy the `https://` URL provided by Ngrok (e.g., `https://abc123.ngrok.io`).  
5. In the [Instagram Developer Dashboard](https://developers.facebook.com/apps/), set this URL as your **Webhook URL**.

---

## Features
- AI-powered responses using OpenAI GPT-4.
- SQLite database for message history.
- Auto-replies to Instagram DMs and comments.

---

## Troubleshooting
- **"Module Not Found"**: Ensure the virtual environment is activated and dependencies are installed.  
- **Webhook Errors**: Verify the Ngrok URL is correctly set in the Instagram Dashboard.  
- **Token Issues**: Regenerate tokens and update `.env` if expired.

