import {
  AngularNodeAppEngine,
  createNodeRequestHandler,
  isMainModule,
  writeResponseToNodeResponse,
} from '@angular/ssr/node';
import express from 'express';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as fs from 'node:fs';
import * as https from 'node:https';

const serverDistFolder = dirname(fileURLToPath(import.meta.url));
const browserDistFolder = resolve(serverDistFolder, '../browser');

const app = express();
const angularApp = new AngularNodeAppEngine();

// Your REST API endpoints can go here
// app.get('/api/**', (req, res) => { ... });

app.use(
  express.static(browserDistFolder, {
    maxAge: '1y',
    index: false,
    redirect: false,
  }),
);

app.use('/**', (req, res, next) => {
  angularApp
    .handle(req)
    .then((response) =>
      response ? writeResponseToNodeResponse(response, res) : next(),
    )
    .catch(next);
});

if (isMainModule(import.meta.url)) {
  const port = process.env['PORT'] || 4200;
  
  // Check if we should run in HTTPS mode (for development)
  if (process.env['USE_HTTPS'] === 'true') {
    try {
      // Path to SSL certificates relative to where the server will run
      const sslOptions = {
        key: fs.readFileSync('ssl/private.key'),
        cert: fs.readFileSync('ssl/certificate.crt')
      };
      
      https.createServer(sslOptions, app).listen(port, () => {
        console.log(`Node Express server listening on https://localhost:${port}`);
      });
    } catch (error) {
      console.error('Error starting HTTPS server:', error);
      console.log('Falling back to HTTP...');
      app.listen(port, () => {
        console.log(`Node Express server listening on http://localhost:${port}`);
      });
    }
  } else {
    // Standard HTTP server (for production behind reverse proxy)
    app.listen(port, () => {
      console.log(`Node Express server listening on http://localhost:${port}`);
    });
  }
}

export const reqHandler = createNodeRequestHandler(app);
