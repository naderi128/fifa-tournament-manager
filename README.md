# 🎮 FIFA Tournament Manager (Vercel Edition)

A professional Flask-based web application optimized for Vercel, designed for managing FIFA leagues with friends at gaming centers.

## 🚀 Quick Start (Local)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the app**:
   ```bash
   python api/index.py
   ```
   *Access at: http://127.0.0.1:5000*

## ☁️ Deployment (Vercel)

This app is pre-configured for **Vercel**:
1. Push this code to a GitHub/GitLab/Bitbucket repository.
2. Go to [Vercel](https://vercel.com) and click **"Add New Project"**.
3. Import your repository.
4. Vercel will automatically detect the settings from `vercel.json`.
5. Click **Deploy**.

> [!IMPORTANT]
> **Data Persistence**: Vercel uses serverless functions, meaning the internal state resets. I've built a **Back-up State** button in the Standings tab. Download your state and re-upload it if the app resets. For full automation, add a free MongoDB or Redis database!

## Features
- **Stateless-Ready**: Designed for serverless environments.
- **Modern UI**: Built with Tailwind CSS and premium glassmorphism.
- **Double Round Robin**: Automatic scheduling with ownership constraints.
- **Match Management**: Real-time score entry and Golden Boot tracking.
- **Export Data**: Export standings to TXT or JSON.
