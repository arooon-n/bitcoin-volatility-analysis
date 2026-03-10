#!/usr/bin/env python3
"""
Bitcoin Volatility Analysis Dashboard

Interactive web dashboard for real-time visualization of Bitcoin volatility metrics.
Updates every 10 seconds with the latest data from Spark Structured Streaming.

Features:
- Real-time KPI cards: current price, 24h volatility, volume, last update
- Price and volatility time series chart
- Volatility comparison chart (1h vs 24h)
- Trading volume bar chart
- Automatic refresh every 10 seconds
"""

import glob
import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yaml
from dash import Dash, dcc, html, Input, Output

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s — %(levelname)s — %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class BitcoinDashboard:
    """Bitcoin volatility analysis dashboard with real-time updates."""
    
    def __init__(self, config_path):
        """
        Initialize the dashboard.
        
        Args:
            config_path (Path): Path to configuration YAML file
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.local_data_path = self.config['dashboard']['host_data_path']
        self.update_interval_ms = self.config['dashboard']['update_interval_ms']
        self.port = self.config['dashboard']['port']
        self.host = self.config['dashboard']['host']
        
        # Initialize Dash app
        self.app = Dash(__name__, title="Bitcoin Volatility Dashboard")
        
        # Setup layout
        self._setup_layout()
        
        # Setup callbacks
        self._setup_callbacks()
        
        logger.info("="*60)
        logger.info("  Bitcoin Volatility Dashboard Initialized")
        logger.info("="*60)
        logger.info(f"Data Source: {self.local_data_path}")
        logger.info(f"Update Interval: {self.update_interval_ms/1000:.1f} seconds")
        logger.info(f"Server Port: {self.port}")
        logger.info("="*60)
    
    def load_latest_data(self):
        """
        Load latest data from JSON files written by Spark.
        
        Returns:
            pd.DataFrame: Latest Bitcoin data, or empty DataFrame on error
        """
        try:
            # Find all JSON files
            json_files = glob.glob(f"{self.local_data_path}/*.json")
            
            if not json_files:
                logger.warning(f"No JSON files found in {self.local_data_path}")
                return pd.DataFrame()
            
            # Read all JSON files (JSON Lines format)
            all_records = []
            for json_file in json_files:
                try:
                    with open(json_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                record = json.loads(line)
                                all_records.append(record)
                except Exception as e:
                    logger.warning(f"Error reading {json_file}: {str(e)}")
                    continue
            
            if not all_records:
                logger.warning("No valid records found in JSON files")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(all_records)
            
            # Convert timestamp to datetime
            df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='s')
            
            # Sort by timestamp and keep most recent 1000 records
            df = df.sort_values('timestamp', ascending=True)
            df = df.tail(1000)
            
            logger.info(f"Loaded {len(df)} records. Latest: {df['timestamp_dt'].iloc[-1]}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return pd.DataFrame()
    
    def _setup_layout(self):
        """Setup the dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("Bitcoin Volatility Analysis Dashboard", 
                       style={'color': 'white', 'margin': '0', 'padding': '20px'}),
                html.P("Real-time price and volatility monitoring — updates every 10 seconds",
                      style={'color': 'white', 'margin': '0', 'padding': '0 20px 20px 20px'})
            ], style={
                'backgroundColor': '#1e3a8a',
                'textAlign': 'center'
            }),
            
            # KPI Cards
            html.Div([
                # Current Price Card
                html.Div([
                    html.H3("Current Price", style={'color': '#3b82f6', 'marginBottom': '10px'}),
                    html.H2(id='current-price', children='Loading...', 
                           style={'color': '#1e3a8a', 'margin': '0'})
                ], style={
                    'backgroundColor': 'white',
                    'padding': '20px',
                    'borderRadius': '8px',
                    'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'flex': '1',
                    'margin': '10px'
                }),
                
                # 24h Volatility Card
                html.Div([
                    html.H3("24h Volatility", style={'color': '#ef4444', 'marginBottom': '10px'}),
                    html.H2(id='current-volatility', children='Loading...', 
                           style={'color': '#991b1b', 'margin': '0'})
                ], style={
                    'backgroundColor': 'white',
                    'padding': '20px',
                    'borderRadius': '8px',
                    'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'flex': '1',
                    'margin': '10px'
                }),
                
                # 24h Volume Card
                html.Div([
                    html.H3("24h Volume (USD)", style={'color': '#10b981', 'marginBottom': '10px'}),
                    html.H2(id='current-volume', children='Loading...', 
                           style={'color': '#065f46', 'margin': '0'})
                ], style={
                    'backgroundColor': 'white',
                    'padding': '20px',
                    'borderRadius': '8px',
                    'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'flex': '1',
                    'margin': '10px'
                }),
                
                # Last Update Card
                html.Div([
                    html.H3("Last Update", style={'color': '#8b5cf6', 'marginBottom': '10px'}),
                    html.H2(id='last-update', children='Loading...', 
                           style={'color': '#5b21b6', 'margin': '0', 'fontSize': '18px'})
                ], style={
                    'backgroundColor': 'white',
                    'padding': '20px',
                    'borderRadius': '8px',
                    'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'flex': '1',
                    'margin': '10px'
                })
            ], style={
                'display': 'flex',
                'flexWrap': 'wrap',
                'padding': '20px',
                'backgroundColor': '#f3f4f6'
            }),
            
            # Charts Container
            html.Div([
                # Price and Volatility Chart
                html.Div([
                    dcc.Graph(id='price-volatility-chart')
                ], style={'padding': '20px'}),
                
                # Volatility Comparison Chart
                html.Div([
                    dcc.Graph(id='volatility-metrics-chart')
                ], style={'padding': '20px'}),
                
                # Volume Chart
                html.Div([
                    dcc.Graph(id='volume-chart')
                ], style={'padding': '20px'})
            ], style={'backgroundColor': '#f3f4f6'}),
            
            # Footer
            html.Div([
                html.P("Data source: CryptoCompare API | Processed by Apache Spark Structured Streaming",
                      style={'color': '#6b7280', 'margin': '0', 'padding': '20px', 'textAlign': 'center'})
            ], style={'backgroundColor': 'white'}),
            
            # Auto-refresh interval
            dcc.Interval(
                id='interval-component',
                interval=self.update_interval_ms,
                n_intervals=0
            )
        ])
    
    def _setup_callbacks(self):
        """Setup Dash callbacks for auto-updating components."""
        
        @self.app.callback(
            [
                Output('current-price', 'children'),
                Output('current-volatility', 'children'),
                Output('current-volume', 'children'),
                Output('last-update', 'children'),
                Output('price-volatility-chart', 'figure'),
                Output('volatility-metrics-chart', 'figure'),
                Output('volume-chart', 'figure')
            ],
            [Input('interval-component', 'n_intervals')]
        )
        def update_dashboard(n):
            """
            Update all dashboard components with latest data.
            
            Args:
                n (int): Interval counter (unused, triggers callback)
                
            Returns:
                tuple: Updated values for all output components
            """
            # Load latest data
            df = self.load_latest_data()
            
            # Handle empty data
            if df.empty:
                return (
                    "No data yet",
                    "No data yet",
                    "No data yet",
                    "No data yet",
                    go.Figure(),
                    go.Figure(),
                    go.Figure()
                )
            
            # Get latest values for KPI cards
            latest = df.iloc[-1]
            
            current_price = f"${latest['price']:,.2f}"
            
            current_volatility = f"{latest['volatility_24h']:.6f}" if pd.notna(latest['volatility_24h']) else "N/A"
            
            current_volume = f"${latest['volume24h']:,.0f}" if pd.notna(latest['volume24h']) else "N/A"
            
            last_update = datetime.fromisoformat(latest['datetime'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
            
            # Chart 1: Price and Volatility
            fig1 = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                row_heights=[0.6, 0.4],
                subplot_titles=('Bitcoin Price (USD)', '24h Volatility')
            )
            
            # Price trace
            fig1.add_trace(
                go.Scatter(
                    x=df['timestamp_dt'],
                    y=df['price'],
                    name='BTC Price',
                    line=dict(color='#3b82f6', width=2)
                ),
                row=1, col=1
            )
            
            # Moving averages (if available)
            if 'price_ma_1h' in df.columns and df['price_ma_1h'].notna().any():
                fig1.add_trace(
                    go.Scatter(
                        x=df['timestamp_dt'],
                        y=df['price_ma_1h'],
                        name='1h MA',
                        line=dict(color='#f97316', width=1, dash='dash')
                    ),
                    row=1, col=1
                )
            
            if 'price_ma_24h' in df.columns and df['price_ma_24h'].notna().any():
                fig1.add_trace(
                    go.Scatter(
                        x=df['timestamp_dt'],
                        y=df['price_ma_24h'],
                        name='24h MA',
                        line=dict(color='#10b981', width=1, dash='dash')
                    ),
                    row=1, col=1
                )
            
            # Volatility trace
            fig1.add_trace(
                go.Scatter(
                    x=df['timestamp_dt'],
                    y=df['volatility_24h'],
                    name='Volatility',
                    line=dict(color='#ef4444', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(239, 68, 68, 0.1)'
                ),
                row=2, col=1
            )
            
            fig1.update_xaxes(title_text="Time", row=2, col=1)
            fig1.update_yaxes(title_text="Price (USD)", row=1, col=1)
            fig1.update_yaxes(title_text="Volatility", row=2, col=1)
            
            fig1.update_layout(
                height=500,
                hovermode='x unified',
                paper_bgcolor='#F8F9FA',
                plot_bgcolor='white',
                showlegend=True,
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            
            # Chart 2: Volatility Comparison (1h vs 24h)
            fig2 = go.Figure()
            
            if 'volatility_1h' in df.columns and df['volatility_1h'].notna().any():
                fig2.add_trace(
                    go.Scatter(
                        x=df['timestamp_dt'],
                        y=df['volatility_1h'],
                        name='1h Volatility',
                        line=dict(color='#8b5cf6', width=2)
                    )
                )
            
            fig2.add_trace(
                go.Scatter(
                    x=df['timestamp_dt'],
                    y=df['volatility_24h'],
                    name='24h Volatility',
                    line=dict(color='#ef4444', width=2)
                )
            )
            
            fig2.update_layout(
                title='Volatility Comparison: 1h vs 24h',
                xaxis_title='Time',
                yaxis_title='Volatility',
                height=380,
                hovermode='x unified',
                paper_bgcolor='#F8F9FA',
                plot_bgcolor='white'
            )
            
            # Chart 3: Volume
            fig3 = go.Figure()
            
            fig3.add_trace(
                go.Bar(
                    x=df['timestamp_dt'],
                    y=df['volume24h'],
                    name='Volume',
                    marker_color='#10b981'
                )
            )
            
            fig3.update_layout(
                title='Trading Volume (24h USD)',
                xaxis_title='Time',
                yaxis_title='Volume (USD)',
                height=280,
                paper_bgcolor='#F8F9FA',
                plot_bgcolor='white'
            )
            
            return (
                current_price,
                current_volatility,
                current_volume,
                last_update,
                fig1,
                fig2,
                fig3
            )
    
    def run(self):
        """Start the dashboard server."""
        print()
        print("="*60)
        print("  Bitcoin Volatility Dashboard")
        print("="*60)
        print(f"Server starting on http://{self.host}:{self.port}")
        print(f"Data source: {self.local_data_path}")
        print(f"Auto-refresh: every {self.update_interval_ms/1000:.1f} seconds")
        print("="*60)
        print("\nOpen your browser and navigate to:")
        print(f"  http://localhost:{self.port}")
        print("\nPress Ctrl+C to stop the server")
        print()
        
        self.app.run_server(
            debug=True,
            host=self.host,
            port=self.port
        )


def main():
    """Main entry point."""
    # Get config path
    script_dir = Path(__file__).parent
    config_path = script_dir.parent / "config" / "config.yaml"
    
    if not config_path.exists():
        print(f"ERROR: Configuration file not found at {config_path}")
        return
    
    try:
        dashboard = BitcoinDashboard(config_path)
        dashboard.run()
    except KeyboardInterrupt:
        print("\n\nDashboard stopped by user.")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
