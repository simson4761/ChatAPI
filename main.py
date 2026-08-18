from fastapi import FastAPI

app = FastAPI()


@app.get("/new-messages")
def newMessages():
    return {
        "new": "message"
    }


@app.get("/send-message")
def sendMessage():
    return {
        "message": "sent"
    }


@app.get("/delete-message")
def deleteMessage():
    return {
        "message": "deleted"
    }


@app.get("/update-message")
def updateMessage():
    return {
        "message": "updated"
    }
