const { app, BrowserWindow } = require('electron');  
const path = require('path');  

// main.js (add to the top)  
const { ipcMain } = require('electron');  
const { spawn } = require('child_process');  
 
// Listen for "run-python" event from the renderer  
ipcMain.on('run-python', (event, inputText) => {  
  // Spawn a Python process  
  const pythonProcess = spawn('python3', [path.join(__dirname, 'backend/script.py')]);  
 
  // Send input to Python via stdin  
  pythonProcess.stdin.write(inputText + '\n');  
  pythonProcess.stdin.end();  
 
  // Capture Python’s output  
  pythonProcess.stdout.on('data', (data) => {  
    event.reply('python-result', data.toString());  // Send result back to renderer  
  });  
 
  // Handle errors  
  pythonProcess.stderr.on('data', (data) => {  
    console.error(`Python error: ${data}`);  
  });  
});
 
// Create the main window  
function createWindow() {  
  const mainWindow = new BrowserWindow({  
    width: 800,  
    height: 600,  
    webPreferences: {  
      nodeIntegration: true,  // Enable Node.js in the renderer (for development only!)  
      contextIsolation: false  // Disable context isolation (for simplicity; use IPC in production)  
    }  
  });  
 
  // Load the UI (index.html)  
  mainWindow.loadFile('index.html');  
 
  // Open DevTools (for debugging)  
  mainWindow.webContents.openDevTools();  
}  
 
// Launch the app when Electron is ready  
app.whenReady().then(() => {  
  createWindow();  
 
  app.on('activate', () => {  
    if (BrowserWindow.getAllWindows().length === 0) createWindow();  
  });  
});  
 
// Quit when all windows are closed (except macOS)  
app.on('window-all-closed', () => {  
  if (process.platform !== 'darwin') app.quit();  
}); 