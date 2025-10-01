"""
Stock Market Analysis and Prediction Module for Telegram Bot
Provides comprehensive stock analysis, technical indicators, and AI predictions
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Optional, Tuple
import asyncio
import warnings
warnings.filterwarnings('ignore')

# Try to import ML libraries, fall back gracefully if not available
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False


class StockAnalyzer:
    """Advanced stock analysis with technical indicators and predictions"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes cache
        
    def get_stock_data(self, symbol: str, period: str = "6mo") -> Optional[pd.DataFrame]:
        """Get stock data from Yahoo Finance with improved error handling"""
        try:
            # Clean symbol
            symbol = symbol.upper().strip()
            
            # Check cache
            cache_key = f"{symbol}_{period}"
            if cache_key in self.cache:
                cached_time, data = self.cache[cache_key]
                if datetime.now().timestamp() - cached_time < self.cache_timeout:
                    return data
            
            # Create session with proper headers to avoid rate limiting
            import requests
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            # Special case for testing - return mock data for TEST symbol
            if symbol == "TEST":
                mock_data = self.generate_mock_data()
                self.cache[cache_key] = (datetime.now().timestamp(), mock_data)
                return mock_data
            
            # Try different periods if the requested one fails
            periods_to_try = [period, "3mo", "1mo", "5d", "1d"]
            if period not in periods_to_try:
                periods_to_try.insert(0, period)
                
            for try_period in periods_to_try:
                try:
                    ticker = yf.Ticker(symbol, session=session)
                    data = ticker.history(period=try_period)
                    
                    if not data.empty and len(data) >= 5:  # Need at least 5 days for analysis
                        # Cache successful result
                        self.cache[cache_key] = (datetime.now().timestamp(), data)
                        return data
                    elif not data.empty:
                        # If we have some data but not enough, still cache it
                        self.cache[cache_key] = (datetime.now().timestamp(), data)
                        return data
                        
                except Exception as e:
                    print(f"Failed to fetch {symbol} with period {try_period}: {e}")
                    continue
                    
            return None
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
    
    def generate_mock_data(self) -> pd.DataFrame:
        """Generate mock stock data for testing purposes"""
        import numpy as np
        from datetime import datetime, timedelta
        
        # Generate 60 days of mock data
        dates = pd.date_range(start=datetime.now() - timedelta(days=60), 
                             end=datetime.now(), freq='D')
        
        # Simple random walk for stock price
        np.random.seed(42)  # For consistent results
        base_price = 150.0
        returns = np.random.normal(0.001, 0.02, len(dates))  # 0.1% daily return, 2% volatility
        
        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # Generate OHLCV data
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            daily_vol = abs(np.random.normal(0, 0.01))  # Daily volatility
            high = price * (1 + daily_vol)
            low = price * (1 - daily_vol)
            volume = int(np.random.uniform(1000000, 5000000))  # Random volume
            
            data.append({
                'Open': price * (1 + np.random.normal(0, 0.005)),
                'High': high,
                'Low': low,
                'Close': price,
                'Volume': volume
            })
        
        df = pd.DataFrame(data, index=dates)
        return df
    
    def get_stock_info(self, symbol: str) -> Dict:
        """Get basic stock information"""
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            
            return {
                'symbol': symbol.upper(),
                'name': info.get('longName', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('forwardPE', 'N/A'),
                'dividend_yield': info.get('dividendYield', 0),
                'beta': info.get('beta', 'N/A'),
                'website': info.get('website', 'N/A')
            }
        except Exception as e:
            return {'error': str(e)}
    
    def calculate_technical_indicators(self, data: pd.DataFrame) -> Dict:
        """Calculate technical indicators"""
        if data is None or data.empty:
            return {}
            
        try:
            indicators = {}
            
            # Basic calculations
            current_price = data['Close'].iloc[-1]
            prev_price = data['Close'].iloc[-2] if len(data) > 1 else current_price
            price_change = current_price - prev_price
            price_change_pct = (price_change / prev_price) * 100 if prev_price != 0 else 0
            
            # Moving Averages
            data['SMA_20'] = data['Close'].rolling(window=20).mean()
            data['SMA_50'] = data['Close'].rolling(window=50).mean()
            data['EMA_12'] = data['Close'].ewm(span=12).mean()
            data['EMA_26'] = data['Close'].ewm(span=26).mean()
            
            # RSI calculation
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # MACD
            macd_line = data['EMA_12'] - data['EMA_26']
            signal_line = macd_line.ewm(span=9).mean()
            histogram = macd_line - signal_line
            
            # Bollinger Bands
            sma_20 = data['SMA_20']
            std_20 = data['Close'].rolling(window=20).std()
            upper_band = sma_20 + (2 * std_20)
            lower_band = sma_20 - (2 * std_20)
            
            # Volume indicators
            avg_volume = data['Volume'].rolling(window=20).mean().iloc[-1]
            current_volume = data['Volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Support and Resistance (simple calculation)
            recent_highs = data['High'].tail(20)
            recent_lows = data['Low'].tail(20)
            resistance = recent_highs.max()
            support = recent_lows.min()
            
            indicators = {
                'current_price': round(current_price, 2),
                'price_change': round(price_change, 2),
                'price_change_pct': round(price_change_pct, 2),
                'sma_20': round(data['SMA_20'].iloc[-1], 2) if not pd.isna(data['SMA_20'].iloc[-1]) else None,
                'sma_50': round(data['SMA_50'].iloc[-1], 2) if not pd.isna(data['SMA_50'].iloc[-1]) else None,
                'rsi': round(rsi.iloc[-1], 2) if not pd.isna(rsi.iloc[-1]) else None,
                'macd': round(macd_line.iloc[-1], 4) if not pd.isna(macd_line.iloc[-1]) else None,
                'macd_signal': round(signal_line.iloc[-1], 4) if not pd.isna(signal_line.iloc[-1]) else None,
                'macd_histogram': round(histogram.iloc[-1], 4) if not pd.isna(histogram.iloc[-1]) else None,
                'upper_band': round(upper_band.iloc[-1], 2) if not pd.isna(upper_band.iloc[-1]) else None,
                'lower_band': round(lower_band.iloc[-1], 2) if not pd.isna(lower_band.iloc[-1]) else None,
                'volume_ratio': round(volume_ratio, 2),
                'avg_volume': int(avg_volume) if not pd.isna(avg_volume) else 0,
                'current_volume': int(current_volume),
                'support': round(support, 2),
                'resistance': round(resistance, 2)
            }
            
            return indicators
            
        except Exception as e:
            return {'error': str(e)}
    
    def generate_signals(self, indicators: Dict) -> Dict:
        """Generate trading signals based on technical indicators"""
        signals = {
            'overall': 'NEUTRAL',
            'strength': 0,  # -100 to +100
            'signals': []
        }
        
        try:
            score = 0
            signal_count = 0
            
            # RSI signals
            if indicators.get('rsi'):
                rsi = indicators['rsi']
                if rsi < 30:
                    signals['signals'].append("🟢 RSI Oversold - Potential Buy")
                    score += 20
                elif rsi > 70:
                    signals['signals'].append("🔴 RSI Overbought - Potential Sell")
                    score -= 20
                else:
                    signals['signals'].append(f"🟡 RSI Neutral ({rsi})")
                signal_count += 1
            
            # Moving Average signals
            current_price = indicators.get('current_price', 0)
            sma_20 = indicators.get('sma_20')
            sma_50 = indicators.get('sma_50')
            
            if sma_20 and sma_50 and current_price:
                if sma_20 > sma_50 and current_price > sma_20:
                    signals['signals'].append("🟢 Price above MAs - Uptrend")
                    score += 15
                elif sma_20 < sma_50 and current_price < sma_20:
                    signals['signals'].append("🔴 Price below MAs - Downtrend")
                    score -= 15
                else:
                    signals['signals'].append("🟡 Mixed MA signals")
                signal_count += 1
            
            # MACD signals
            macd = indicators.get('macd')
            macd_signal = indicators.get('macd_signal')
            
            if macd is not None and macd_signal is not None:
                if macd > macd_signal:
                    signals['signals'].append("🟢 MACD Bullish")
                    score += 10
                else:
                    signals['signals'].append("🔴 MACD Bearish")
                    score -= 10
                signal_count += 1
            
            # Bollinger Bands
            upper_band = indicators.get('upper_band')
            lower_band = indicators.get('lower_band')
            
            if upper_band and lower_band and current_price:
                if current_price <= lower_band:
                    signals['signals'].append("🟢 Price at Lower Band - Oversold")
                    score += 15
                elif current_price >= upper_band:
                    signals['signals'].append("🔴 Price at Upper Band - Overbought")
                    score -= 15
                else:
                    signals['signals'].append("🟡 Price within Bollinger Bands")
                signal_count += 1
            
            # Volume analysis
            volume_ratio = indicators.get('volume_ratio', 1)
            if volume_ratio > 2:
                signals['signals'].append(f"📈 High Volume ({volume_ratio:.1f}x avg)")
                score += 5
            elif volume_ratio < 0.5:
                signals['signals'].append(f"📉 Low Volume ({volume_ratio:.1f}x avg)")
                score -= 5
            else:
                signals['signals'].append(f"📊 Normal Volume ({volume_ratio:.1f}x avg)")
            
            # Calculate overall signal
            if signal_count > 0:
                signals['strength'] = min(100, max(-100, int(score / signal_count * 5)))
                
                if signals['strength'] > 30:
                    signals['overall'] = 'BULLISH'
                elif signals['strength'] < -30:
                    signals['overall'] = 'BEARISH'
                else:
                    signals['overall'] = 'NEUTRAL'
            
            return signals
            
        except Exception as e:
            signals['error'] = str(e)
            return signals
    
    def simple_prediction(self, data: pd.DataFrame, days: int = 5) -> Dict:
        """Simple price prediction using linear regression"""
        if data is None or len(data) < 30:
            return {'error': 'Insufficient data for prediction'}
        
        try:
            # Prepare features
            df = data.copy()
            df['Days'] = range(len(df))
            df['SMA_5'] = df['Close'].rolling(5).mean()
            df['SMA_10'] = df['Close'].rolling(10).mean()
            df['Volume_MA'] = df['Volume'].rolling(5).mean()
            
            # Calculate price momentum
            df['Price_Change'] = df['Close'].pct_change()
            df['Volume_Change'] = df['Volume'].pct_change()
            
            # Drop NaN values
            df = df.dropna()
            
            if len(df) < 20:
                return {'error': 'Insufficient clean data'}
            
            # Simple trend analysis
            recent_prices = df['Close'].tail(10).values
            trend = np.polyfit(range(10), recent_prices, 1)[0]  # Linear trend
            
            current_price = df['Close'].iloc[-1]
            
            # Simple prediction based on trend and volatility
            volatility = df['Close'].tail(20).std()
            
            predictions = []
            for day in range(1, days + 1):
                # Simple linear extrapolation with some randomness consideration
                predicted_price = current_price + (trend * day)
                
                # Add confidence interval based on volatility
                confidence_range = volatility * np.sqrt(day) * 1.96  # 95% confidence
                
                predictions.append({
                    'day': day,
                    'predicted_price': round(predicted_price, 2),
                    'lower_bound': round(predicted_price - confidence_range, 2),
                    'upper_bound': round(predicted_price + confidence_range, 2),
                    'confidence': max(20, 90 - (day * 10))  # Decreasing confidence
                })
            
            return {
                'predictions': predictions,
                'trend': 'UP' if trend > 0 else 'DOWN' if trend < 0 else 'SIDEWAYS',
                'trend_strength': abs(trend),
                'volatility': round(volatility, 2),
                'method': 'Linear Trend Analysis'
            }
            
        except Exception as e:
            return {'error': str(e)}

    def ml_prediction(self, data: pd.DataFrame, days: int = 5) -> Dict:
        """Advanced ML-based prediction using Random Forest"""
        if not ML_AVAILABLE:
            return self.simple_prediction(data, days)
        
        if data is None or len(data) < 50:
            return {'error': 'Insufficient data for ML prediction'}
        
        try:
            # Prepare features for ML
            df = data.copy()
            
            # Technical indicators as features
            df['SMA_5'] = df['Close'].rolling(5).mean()
            df['SMA_10'] = df['Close'].rolling(10).mean()
            df['SMA_20'] = df['Close'].rolling(20).mean()
            df['EMA_12'] = df['Close'].ewm(span=12).mean()
            
            # Price momentum features
            df['Price_Change_1d'] = df['Close'].pct_change(1)
            df['Price_Change_5d'] = df['Close'].pct_change(5)
            df['Volume_Change'] = df['Volume'].pct_change()
            
            # Volatility
            df['Volatility'] = df['Close'].rolling(10).std()
            
            # High-Low spread
            df['HL_Spread'] = (df['High'] - df['Low']) / df['Close']
            
            # Volume ratio
            df['Volume_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
            
            # Target: next day's price change
            df['Target'] = df['Close'].shift(-1) - df['Close']
            
            # Drop NaN values
            df = df.dropna()
            
            if len(df) < 30:
                return {'error': 'Insufficient clean data for ML'}
            
            # Prepare features and target
            feature_columns = ['SMA_5', 'SMA_10', 'SMA_20', 'EMA_12', 'Price_Change_1d', 
                             'Price_Change_5d', 'Volume_Change', 'Volatility', 'HL_Spread', 'Volume_Ratio']
            
            X = df[feature_columns].values
            y = df['Target'].values
            
            # Split data
            train_size = int(len(X) * 0.8)
            X_train, X_test = X[:train_size], X[train_size:]
            y_train, y_test = y[:train_size], y[train_size:]
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10)
            model.fit(X_train_scaled, y_train)
            
            # Calculate accuracy on test set
            test_predictions = model.predict(X_test_scaled)
            accuracy = np.mean(np.abs(test_predictions - y_test) < np.std(y_test)) * 100
            
            # Make predictions for future days
            current_features = X[-1:].reshape(1, -1)
            current_features_scaled = scaler.transform(current_features)
            current_price = df['Close'].iloc[-1]
            
            predictions = []
            for day in range(1, days + 1):
                # Predict price change
                price_change_pred = model.predict(current_features_scaled)[0]
                predicted_price = current_price + price_change_pred
                
                # Calculate confidence based on model uncertainty and time horizon
                confidence = max(30, accuracy - (day * 10))
                
                # Estimate prediction interval
                price_std = np.std(y_test)
                margin = price_std * day * 0.5
                
                predictions.append({
                    'day': day,
                    'predicted_price': round(predicted_price, 2),
                    'lower_bound': round(predicted_price - margin, 2),
                    'upper_bound': round(predicted_price + margin, 2),
                    'confidence': round(confidence, 1)
                })
                
                current_price = predicted_price
            
            return {
                'predictions': predictions,
                'model_accuracy': round(accuracy, 1),
                'method': 'Random Forest ML',
                'features_used': len(feature_columns),
                'training_samples': len(X_train)
            }
            
        except Exception as e:
            return {'error': str(e)}

    async def analyze_stock(self, symbol: str, prediction_days: int = 5) -> Dict:
        """Complete stock analysis with improved error handling"""
        try:
            # Validate symbol
            symbol = symbol.upper().strip()
            if not symbol or len(symbol) > 10:
                return {'error': f'Invalid stock symbol: {symbol}'}
            
            # Get stock data with better error messaging
            data = self.get_stock_data(symbol)
            if data is None:
                return {
                    'error': f'Could not fetch data for {symbol}. This could be due to:\n'
                             f'• Invalid or delisted symbol\n'
                             f'• Yahoo Finance API rate limiting\n'
                             f'• Network connectivity issues\n'
                             f'• Market closure (try again during market hours)'
                }
            
            if data.empty:
                return {'error': f'No data available for {symbol}'}
            
            if len(data) < 5:
                return {'error': f'Insufficient data for {symbol} (only {len(data)} days available)'}
            
            # Get basic info
            info = self.get_stock_info(symbol)
            
            # Calculate technical indicators
            indicators = self.calculate_technical_indicators(data)
            
            # Generate signals
            signals = self.generate_signals(indicators)
            
            # Get predictions
            if ML_AVAILABLE and len(data) >= 50:
                predictions = self.ml_prediction(data, prediction_days)
            else:
                predictions = self.simple_prediction(data, prediction_days)
            
            return {
                'symbol': symbol.upper(),
                'timestamp': datetime.now().isoformat(),
                'basic_info': info,
                'technical_indicators': indicators,
                'signals': signals,
                'predictions': predictions,
                'data_points': len(data),
                'ml_available': ML_AVAILABLE
            }
            
        except Exception as e:
            return {'error': str(e)}


def format_stock_analysis(analysis: Dict) -> str:
    """Format stock analysis results for Telegram"""
    if 'error' in analysis:
        return f"❌ **שגיאה בניתוח:** {analysis['error']}"
    
    symbol = analysis['symbol']
    info = analysis.get('basic_info', {})
    indicators = analysis.get('technical_indicators', {})
    signals = analysis.get('signals', {})
    predictions = analysis.get('predictions', {})
    
    # Build response
    response = f"📈 **ניתוח מניה - {symbol}**\n\n"
    
    # Basic info
    if 'name' in info:
        response += f"🏢 **חברה:** {info['name']}\n"
    if 'sector' in info and info['sector'] != 'N/A':
        response += f"🏭 **סקטור:** {info['sector']}\n"
    
    # Current price and change
    if 'current_price' in indicators:
        price = indicators['current_price']
        change = indicators.get('price_change', 0)
        change_pct = indicators.get('price_change_pct', 0)
        
        direction = "📈" if change >= 0 else "📉"
        response += f"\n💰 **מחיר נוכחי:** ${price}\n"
        response += f"{direction} **שינוי:** ${change:.2f} ({change_pct:.2f}%)\n"
    
    # Technical indicators
    response += f"\n🔧 **מחוונים טכניים:**\n"
    
    if 'rsi' in indicators and indicators['rsi']:
        rsi = indicators['rsi']
        rsi_status = "🔴 Overbought" if rsi > 70 else "🟢 Oversold" if rsi < 30 else "🟡 Neutral"
        response += f"• **RSI:** {rsi:.1f} {rsi_status}\n"
    
    if 'sma_20' in indicators and indicators['sma_20']:
        response += f"• **SMA 20:** ${indicators['sma_20']}\n"
    
    if 'volume_ratio' in indicators:
        vol_ratio = indicators['volume_ratio']
        vol_status = "🔥 High" if vol_ratio > 1.5 else "❄️ Low" if vol_ratio < 0.5 else "📊 Normal"
        response += f"• **Volume:** {vol_status} ({vol_ratio:.1f}x avg)\n"
    
    # Signals
    if 'overall' in signals:
        overall = signals['overall']
        strength = signals.get('strength', 0)
        
        signal_emoji = "🟢" if overall == 'BULLISH' else "🔴" if overall == 'BEARISH' else "🟡"
        response += f"\n{signal_emoji} **Signal:** {overall}"
        if strength != 0:
            response += f" (Strength: {strength})\n"
        else:
            response += "\n"
        
        # Top signals
        if 'signals' in signals and signals['signals']:
            response += "\n**Top Signals:**\n"
            for signal in signals['signals'][:3]:
                response += f"• {signal}\n"
    
    # Predictions
    if 'predictions' in predictions and predictions['predictions']:
        response += f"\n🔮 **תחזיות מחיר:**\n"
        response += f"**Method:** {predictions.get('method', 'Unknown')}\n"
        
        if 'model_accuracy' in predictions:
            response += f"**Accuracy:** {predictions['model_accuracy']}%\n"
        
        response += "\n"
        for pred in predictions['predictions'][:3]:  # Show first 3 days
            day = pred['day']
            price = pred['predicted_price']
            conf = pred['confidence']
            response += f"• **Day {day}:** ${price} (Confidence: {conf}%)\n"
    
    # Support/Resistance
    if 'support' in indicators and 'resistance' in indicators:
        response += f"\n🎯 **Levels:**\n"
        response += f"• **Support:** ${indicators['support']}\n"
        response += f"• **Resistance:** ${indicators['resistance']}\n"
    
    response += f"\n📊 **Data Points:** {analysis.get('data_points', 0)}\n"
    response += f"⚡ **ML Available:** {'Yes' if analysis.get('ml_available') else 'No'}"
    
    return response


# Initialize the analyzer
stock_analyzer = StockAnalyzer()