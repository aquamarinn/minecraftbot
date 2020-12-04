# written in python 3.8.6

import os
from enum import Enum
import discord
from dotenv import load_dotenv
import boto3
from mcstatus import MinecraftServer

class MCServer:
    def __init__(self, server_instance_id:str) -> None:
        self.INSTANCE_ID = server_instance_id
    
    def setup(self) -> int:

        self.ec2client = boto3.client('ec2',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('REGION_NAME'))
        
        try:
            response = self.ec2client.describe_instances(InstanceIds=[self.INSTANCE_ID],DryRun=False)['Reservations'][0]['Instances'][0]

            self.CONNECTED = True
            return 1
        except:
            print('An error occured. Cannot establish connection to the server, AWS access ID or Key might be incorrect. Please check .env file.')
            self.CONNECTED = False
            return 0

    def getState(self) -> str:
        if self.CONNECTED:
            self.EC2_STATE = self.ec2client.describe_instances(InstanceIds=[self.INSTANCE_ID],DryRun=False)['Reservations'][0]['Instances'][0]['State']['Name']
            try: 
                if self.EC2_STATE == 'running':
                    server = MinecraftServer(self.PUBLIC_DNS_NAME, 25565)
                    status = server.status()
                    self.numberOfPlayersOnline = status.players.online
                    self.MC_SERVER_STATUS = 'online'
                else:
                    self.numberOfPlayersOnline = 0
                    self.MC_SERVER_STATUS == 'offline'
            except:
                self.numberOfPlayersOnline = 0
                self.MC_SERVER_STATUS = 'offline'
            finally:
                return f'```EC2 instance: {self.EC2_STATE}\nMC server: {self.MC_SERVER_STATUS}\nPlayers Online: {self.numberOfPlayersOnline}```'
        else:
            return 'Not connected to AWS. Cannot retrieve current state.'

    def getIP(self) -> str:
        if self.CONNECTED:
            response = self.ec2client.describe_instances(InstanceIds=[self.INSTANCE_ID],DryRun=False)['Reservations'][0]['Instances'][0]
            
            self.PUBLIC_DNS_NAME = response['PublicDnsName']
            self.PUBLIC_IP_Address = response['PublicIpAddress']

            return f'```Server IPv4 Address: {self.PUBLIC_IP_Address}\nServer Public DNS Name: {self.PUBLIC_DNS_NAME}```'
        else:
            return 'Not connected to AWS. Cannot retrieve IP.'

    def start(self) -> str:
        if self.CONNECTED:
            self.getState()
            if self.EC2_STATE == 'stopped':
                response = self.ec2client.start_instances(InstanceIds=[self.INSTANCE_ID], DryRun=False)
                print(f'Starting EC2 Instance: {self.INSTANCE_ID}')
                return 'Starting server.'
            else:
                return f'Cannot start server right now.\nThe server is currently: {self.EC2_STATE}'
        else:
            return 'Not connected to AWS. Cannot start EC2 instance.'
    
    def stop(self) -> str:
        if self.CONNECTED:
            self.getState()
            if self.EC2_STATE == 'running':
                if self.numberOfPlayersOnline == 0:
                    response = self.ec2client.start_instances(InstanceIds=[self.INSTANCE_ID], DryRun=False)
                    print(f'Starting EC2 Instance: {self.INSTANCE_ID}')
                    return 'Stopping server.'
                else:
                    return f'Cannot stop server right now. Someone is still online.'
            else:
                return f'Cannot stop server right now.\nThe server is currently: {self.EC2_STATE}.'
        else:
            return 'Not connected to AWS. Cannot stop EC2 instance.'
    

class DiscordBot(discord.Client):

    Commands = Enum('Commands', ['help', 'server < start | stop | status | ip >'])

    async def on_ready(self) -> None:
        print(f'Logged on as {format(self.user)}!')
        
        self.MCServer = MCServer(server_instance_id=os.getenv('SERVER_INSTANCE_ID'))
        response = self.MCServer.setup()

        if response == 1:
            print('Connection to the EC2 instance has been established successfully.')
        elif response == 0:
            print('Could not connect to the EC2 instance. Please check the .env file if it was configured properly.')
            del self.MCServer
        else:
            pass

    async def on_message(self, message) -> None:
        # so that the bot will not listen it itself.
        if message.author == client.user:
            return

        if message.content.startswith('/help'):
            commandsList = ''
            for command in self.Commands:
                commandsList += f'/{command.name} \n'
            await message.channel.send(f'The following commands are available:\n```{commandsList}```')
        
        if message.content.startswith('/server'):
            try:
                requestedCommand = message.content.split()[1]
                returnmsg = {'start': self.MCServer.start, 
                              'stop': self.MCServer.stop, 
                                'ip': self.MCServer.getIP,
                            'status': self.MCServer.getState}[requestedCommand]()
                    
                if returnmsg != '' or returnmsg != None:
                    await message.channel.send(returnmsg)
            except KeyError:
                    await message.channel.send('Unknown command.\nType /help for a list of available commands.')
            except IndexError:
                await message.channel.send('Unknown command.\nType /help for a list of available commands.')
                
load_dotenv()
DISCORDBOT_TOKEN = os.getenv('DISCORDBOT_TOKEN')

client = DiscordBot()
client.run(DISCORDBOT_TOKEN)

