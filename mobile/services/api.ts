import axios from 'axios';

const api = axios.create({
  baseURL: __DEV__ ? 'http://192.168.1.100:8000' : 'https://api.your-domain.com',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

export default api;
