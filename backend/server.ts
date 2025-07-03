import express from 'express';
import cors from 'cors';
import { createProxyMiddleware } from 'http-proxy-middleware';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.static('frontend'));  // Serve o HTML/JS do mapa

// Proxy para seu GeoServer via NGROK
app.use('/geoserver', createProxyMiddleware({
  target: 'http://localhost:8080',
  changeOrigin: true,
  pathRewrite: { '^/geoserver': '/geoserver' },
}));

app.listen(PORT, () => {
  console.log(`Servidor rodando em http://localhost:${PORT}`);
});

