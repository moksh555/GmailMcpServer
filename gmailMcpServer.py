from fastmcp import FastMCP
import json
from google.cloud import secretmanager
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import pickle
from email.message import EmailMessage
import base64
from config import settings

gmailMcpServer = FastMCP("Gmail")

gmailMcpServer.app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows the MCP Inspector to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def getGmailServices():
    creds = None
    if os.path.exists('token.json'):
        with open('token.json', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client = secretmanager.SecretManagerServiceClient()
            response = client.access_secret_version(request={"name": settings.SECRET_NAME})
            client_config = json.loads(response.payload.data.decode("UTF-8"))
            
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the session token
        with open('token.json', 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

@gmailMcpServer.tool()
def sendEmail(messageBody: str,messageTo: str,messageFrom: str,messageSubject: str):
    """
    Sends an email via the Gmail API.

    Args:
        messageBody (str): The main content of the email.
        messageTo (str): The recipient's email address.
        messageFrom (str): The sender's email address.
        messageSubject (str): The subject line of the email.
    
    Return: 
        str: A confirmation message containing the sent Message ID if successful, or an error message detailing why the send failed.
    """
    try: 
        service = getGmailServices()
        message = EmailMessage()
        message.set_content(messageBody)
        message["To"] = messageTo
        message["From"] = messageFrom
        message["Subject"] = messageSubject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )
        return f"Email sent successfully! Message ID: {send_message['id']}"
    except HttpError as error:
        return f"An error occurred: {error}"

@gmailMcpServer.tool()
def searchMessages(query: str, category: list[str] = ["INBOX"], maxResults: int = 5):
    """
    Search for emails. The AI can provide multiple categories to search simultaneously.
    
    Args:
        query (str): The search query (e.g., 'from:Uber' or 'label:unread').
        category (list[str]): List of labels to filter by (e.g., ['INBOX', 'UNREAD']).
        maxResults (int): Maximum number of messages to return.
    
    Returns:
        str: A formatted string containing message summaries with IDs, metadata, and snippets.
    """
    try:
        service = getGmailServices()
        results = (
            service.users().messages().list(userId="me", q=query, maxResults=maxResults, labelIds=category).execute()
        )
        messages = results.get("messages", [])

        if not messages:
            return "No messages found for that query."

        summary = []
        for message in messages:
            try:
                msg = (
                    service.users().messages().get(userId="me", id=message["id"], format='minimal').execute()
                )
                msgId = msg["id"]
                snippet = msg.get("snippet", "")
                labels = msg.get("labelIds", [])
                msgCategory = next((l for l in labels if l.startswith("CATEGORY_")), "NO_CATEGORY")
                summary.append(f"ID: {msgId}\n"
                    f"/* Metadata: {{ Category: {msgCategory}, Labels: {labels} }} */\n"
                    f"Snippet: {snippet}\n")
            except HttpError:
                continue
        return "\n---\n".join(summary)

    except HttpError as error:
        return f"Gmail Search Error: {error}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    gmailMcpServer.run(
        transport="http", 
        host="0.0.0.0", 
        port=port
    )