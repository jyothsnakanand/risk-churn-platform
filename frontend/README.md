# Risk Churn Platform - Frontend Dashboard

Interactive web dashboard for the E-Commerce Customer Churn Prediction Platform.

## Features

### 📊 Dashboard
- Real-time system status and health monitoring
- Key performance metrics with historical trends
- Live prediction volume tracking
- Model performance comparison charts
- Recent activity feed

### 🔍 Monitoring
- **Drift Detection**: Visual analysis of feature drift with p-value tracking
- **Performance Metrics**: Real-time accuracy, precision, and recall tracking
- **Latency Monitoring**: Request latency distribution and percentiles
- **Outlier Detection**: Anomaly detection for unusual prediction requests

### 🎯 Predictions
- Interactive prediction testing interface
- Pre-loaded sample scenarios (High/Medium/Low risk)
- Real-time risk scoring and churn probability
- Actionable recommendations based on risk level
- Support for all 21 e-commerce features

### ⚙️ Model Management
- Current deployment strategy visualization
- Model v1 vs v2 comparison
- Shadow deployment analysis with metrics
- One-click model promotion and rollback
- Deployment history tracking

### 📈 Analytics
- Customer churn risk distribution
- Feature importance visualization
- Customer segment analysis
- Category and payment method analytics
- Top at-risk customers identification

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **React Router** - Navigation
- **Chart.js / Recharts** - Data visualization
- **Axios** - API client
- **Nginx** - Production web server

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Installation

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Create environment file:
```bash
cp .env.example .env
```

3. Update `.env` with your API URL:
```env
REACT_APP_API_URL=http://localhost:8000
```

### Development

Start the development server:
```bash
npm start
```

The app will open at [http://localhost:3000](http://localhost:3000)

### Building for Production

Build optimized production bundle:
```bash
npm run build
```

The build artifacts will be in the `build/` directory.

### Running Tests

```bash
npm test
```

## Docker Deployment

### Build Docker Image

```bash
docker build -t risk-churn-dashboard:latest .
```

### Run Container

```bash
docker run -p 80:80 \
  -e REACT_APP_API_URL=http://your-api-host:8000 \
  risk-churn-dashboard:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    environment:
      - REACT_APP_API_URL=http://backend:8000
    depends_on:
      - backend
```

## Project Structure

```
frontend/
├── public/              # Static files
│   └── index.html      # HTML template
├── src/
│   ├── components/     # Reusable components
│   │   └── Layout.tsx  # Main layout with sidebar
│   ├── pages/          # Page components
│   │   ├── Dashboard.tsx      # Main dashboard
│   │   ├── Monitoring.tsx     # Drift & monitoring
│   │   ├── Predictions.tsx    # Prediction testing
│   │   ├── ModelManagement.tsx # Model control
│   │   └── Analytics.tsx      # Analytics & insights
│   ├── services/       # API services
│   │   └── api.ts      # API client
│   ├── App.tsx         # Root component
│   └── index.tsx       # Entry point
├── Dockerfile          # Production build
├── nginx.conf          # Nginx configuration
└── package.json        # Dependencies
```

## Features Guide

### Dashboard Page

The main dashboard provides an at-a-glance view of your ML platform:

- **System Status**: Health of platform and models
- **Key Metrics**: Total requests, agreement rate, latency, accuracy
- **Prediction Volume**: Real-time chart showing predictions per minute
- **Model Performance**: Accuracy trends for v1 and v2
- **Shadow Analysis**: Comparison metrics between models
- **Recent Activity**: Latest events and alerts

### Monitoring Page

Monitor model health and detect issues:

**Drift Detection Tab:**
- Bar chart showing p-values for each feature
- Color-coded risk levels (red < 0.05, yellow < 0.1, green > 0.1)
- Table of recent drift events with severity

**Performance Metrics Tab:**
- Line chart tracking accuracy, precision, recall over 24 hours
- Latency distribution histogram
- P50, P95, P99 latency percentiles
- Error rate tracking

**Outlier Detection Tab:**
- Summary of outlier detection status
- List of recent anomalous requests
- Anomaly scores for each request

### Predictions Page

Test predictions interactively:

1. **Load Sample Data**: Click buttons to load pre-configured scenarios
2. **Enter Customer Data**: Fill in all 21 features
3. **Get Prediction**: Submit for real-time churn risk analysis
4. **View Results**: See risk score, probability, model version, latency
5. **Recommendations**: Get actionable retention strategies

Features include:
- Customer demographics (age, account age)
- Purchase behavior (orders, revenue, frequency)
- Engagement metrics (visits, email opens, cart abandonment)
- Customer service (tickets, returns, refunds)
- Preferences (category, discounts, payment method)

### Model Management Page

Control model deployments:

**Current Strategy:**
- Visual display of active routing strategy
- Description of strategy behavior

**Model Comparison:**
- Side-by-side v1 and v2 cards
- Request counts and traffic percentages
- Model specifications and metrics

**Shadow Analysis:**
- Total comparisons between models
- Agreement rate and correlation
- Average prediction difference
- Performance comparison (v1 better vs v2 better)

**Deployment Actions:**
- **Promote v2**: Switch production traffic to v2
- **Rollback to v1**: Revert to v1 if issues detected
- Confirmation dialogs for safety

**Deployment History:**
- Chronological log of all deployments
- Strategy changes and status

### Analytics Page

Deep insights into customer behavior:

**Key Insights:**
- High-risk customer count and percentage
- Engagement trends
- Top retention factors
- Revenue at risk

**Visualizations:**
- Pie chart: Churn risk distribution
- Horizontal bar: Feature importance scores
- Doughnut charts: Categories and payment methods

**Customer Segments:**
- Champions, Loyal, At Risk, Hibernating
- Average revenue and churn rate per segment
- Recommended retention strategies

**Top At-Risk Customers:**
- List of 10 highest-risk customers
- Risk scores, lifetime value, last order date
- Quick action buttons

## API Integration

The dashboard connects to the backend REST API:

### Endpoints Used

- `GET /health` - System health check
- `POST /predict` - Make churn prediction
- `POST /explain` - Get prediction explanation
- `GET /router/metrics` - Routing statistics
- `GET /router/shadow-analysis` - Shadow deployment analysis
- `POST /router/promote-v2` - Promote v2 to production
- `POST /router/rollback` - Rollback to v1
- `GET /metrics` - Prometheus metrics

### Authentication

API key authentication (optional):

```typescript
// API key stored in localStorage
localStorage.setItem('api_key', 'your-api-key');

// Automatically included in requests
apiClient.interceptors.request.use((config) => {
  const apiKey = localStorage.getItem('api_key');
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }
  return config;
});
```

## Customization

### Changing Colors

Edit color variables in CSS files:

```css
/* Primary color */
--primary-color: #4299e1;

/* Success, warning, error */
--success-color: #48bb78;
--warning-color: #ecc94b;
--error-color: #f56565;
```

### Adding New Pages

1. Create page component in `src/pages/`
2. Add route in `App.tsx`
3. Add navigation item in `Layout.tsx`

### Customizing Charts

Charts use Chart.js. Modify options in page components:

```typescript
const chartOptions = {
  responsive: true,
  plugins: {
    legend: { position: 'top' },
  },
  scales: {
    y: { beginAtZero: true },
  },
};
```

## Troubleshooting

### API Connection Issues

- Verify `REACT_APP_API_URL` in `.env`
- Check CORS settings on backend
- Ensure backend is running and accessible

### Build Errors

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Port Already in Use

```bash
# Change port in package.json
"scripts": {
  "start": "PORT=3001 react-scripts start"
}
```

## Performance

- Production build is optimized and minified
- Gzip compression enabled via nginx
- Static assets cached for 1 year
- Code splitting for faster initial load
- Lazy loading for routes (can be implemented)

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

1. Create feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request

## License

Same as main project.
