# Installing Snowbot
This guide is for self-hosting Snowbot. If you just want to install the bot without getting the code, go to https://discord.com/oauth2/authorize?client_id=810377376269205546&scope=bot

## Step One: Install Ubuntu

Enable WSL if you're on windows

## Step Two: Git Clone

Install git with 
sudo apt install git


Cd into your preferred directory and clone the repository with 
git clone https://github.com/Hecate946/Snowbot


## Step Three: Install Postgresql

Install postgresql and postgresql-contrib with the command 
sudo apt install postgresql postgresql-contrib


Switch to your new postgres account with 
sudo -i -u postgres


You should be logged in as a postgres user.

From there, you can access the psql prompt with 
psql


Add a password with 
\password


You will be prompted to enter a password. Don't forget it...

Create the database the bot uses with the command 
CREATE DATABASE <db_name>;


For example, 
CREATE DATABASE Snowbot;
Discord
Discord - A New Way to Chat with Friends & Communities
Discord is the easiest way to communicate over voice, video, and text. Chat, hang out, and stay close with your friends and communities.

## Step Four: Create A Discord Application

Go to [this link](https://discord.com/developers/applications) and create an application.

Go to the bot tab on the left hand side and make your application a bot.

Make sure you enable both privileged gateway intents

![image](https://user-images.githubusercontent.com/83441732/116746625-c5166800-a9ca-11eb-9a4d-64468fb3179c.png)

## Step Five: Pip Install

To install the libraries for Snowbot, navigate to the bot's folder and type 
pip install -r requirements.txt

If you are on windows, do this in cmd instead of ubuntu.

## Step Six: Configure Bot
Run the command:
```yaml
python3 starter.py setup
```
to start an interactive session that will set up your configuration
