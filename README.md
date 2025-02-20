# Instagram AI Bot

This is an AI-powered Instagram bot built using Flask. It:
- Responds to DMs
- Replies to comments on posts
- Sends DMs to users who comment

## Installation Guide

### **1. Install Required Software**
- Install [Python 3.8+](https://www.python.org/downloads/)
- Install [Git](https://git-scm.com/downloads)
- Install [VS Code](https://code.visualstudio.com/)

### **2. Clone the Repository**
```sh
git clone https://github.com/yourusername/your-repo.git
cd your-repo
```

### **3. Create a Virtual Environment**
```sh
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### **4. Install Dependencies**
```sh
pip install -r requirements.txt
```

### **5. Set Up Environment Variables**
Create a `.env` file in the project directory:

```sh
touch .env
```

Edit the `.env` file and add:
```ini
ACCESS_TOKEN=your_instagram_access_token
INSTAGRAM_BUSINESS_ID=your_business_id
VERIFY_TOKEN=your_verification_token
OPENAI_API_KEY=your_openai_key
```

### **6. Generate Instagram Access Token**
To generate the Instagram Access Token, run the Jupyter Notebook:

```sh
jupyter notebook
```
Open `token_generator.ipynb` and follow the steps inside.

### **7. Run the Flask Server**
```sh
python app.py
```
The bot will run on http://127.0.0.1:5000/.

### **8. Set Up Webhook with Ngrok**
To make the bot accessible via the internet, run:

```sh
ngrok http 5000
```
Copy the `https://` URL and set it as your webhook URL in the Instagram Developer Dashboard.

## Features
- AI-powered responses using OpenAI GPT-4.
- Stores message history in an SQLite database.
- Auto-replies to Instagram DMs and comments.
