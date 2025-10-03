"""
Model Memory System - מערכת זיכרון למודל ללמידה עצמית
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd

class ModelMemory:
    def __init__(self, memory_file: str = "model_memory.json"):
        self.memory_file = memory_file
        self.memory = self.load_memory()
    
    def load_memory(self) -> Dict:
        """טען זיכרון מהקובץ"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading memory: {e}")
        
        # מבנה זיכרון ברירת מחדל
        return {
            'predictions_log': [],  # יומן תחזיות
            'model_performance': {},  # ביצועי מודלים
            'market_patterns': {},  # דפוסי שוק שזוהו
            'best_settings': {},  # הגדרות הכי טובות
            'learning_stats': {
                'total_predictions': 0,
                'correct_predictions': 0,
                'accuracy_trend': []
            }
        }
    
    def save_memory(self):
        """שמור זיכרון לקובץ"""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Error saving memory: {e}")
    
    def log_prediction(self, symbol: str, predicted_price: float, 
                      confidence: float, method: str, 
                      prediction_date: str = None):
        """רשום תחזית חדשה"""
        if prediction_date is None:
            prediction_date = datetime.now().isoformat()
        
        prediction_log = {
            'symbol': symbol,
            'predicted_price': predicted_price,
            'confidence': confidence,
            'method': method,
            'prediction_date': prediction_date,
            'target_date': (datetime.now() + timedelta(days=1)).isoformat(),
            'verified': False,
            'actual_price': None,
            'accuracy': None
        }
        
        self.memory['predictions_log'].append(prediction_log)
        self.memory['learning_stats']['total_predictions'] += 1
        
        # שמור רק 1000 התחזיות האחרונות
        if len(self.memory['predictions_log']) > 1000:
            self.memory['predictions_log'] = self.memory['predictions_log'][-1000:]
        
        self.save_memory()
    
    def verify_predictions(self, symbol: str, current_price: float):
        """בדוק תחזיות שעבר הזמן שלהן"""
        today = datetime.now()
        updated = False
        
        for pred in self.memory['predictions_log']:
            if (pred['symbol'] == symbol and 
                not pred['verified'] and 
                datetime.fromisoformat(pred['target_date']) <= today):
                
                # חשב דיוק התחזית
                predicted = pred['predicted_price']
                actual = current_price
                error_percent = abs(predicted - actual) / actual * 100
                
                # התחזית נחשבת נכונה אם הטעות < 5%
                is_correct = error_percent < 5.0
                
                pred['verified'] = True
                pred['actual_price'] = actual
                pred['accuracy'] = 100 - error_percent
                
                if is_correct:
                    self.memory['learning_stats']['correct_predictions'] += 1
                
                updated = True
        
        if updated:
            self._update_accuracy_trend()
            self.save_memory()
    
    def _update_accuracy_trend(self):
        """עדכן מגמת דיוק"""
        verified_predictions = [p for p in self.memory['predictions_log'] if p['verified']]
        
        if len(verified_predictions) >= 10:  # לפחות 10 תחזיות מאומתות
            recent_predictions = verified_predictions[-20:]  # 20 האחרונות
            recent_accuracy = sum(1 for p in recent_predictions if p['accuracy'] > 95) / len(recent_predictions) * 100
            
            self.memory['learning_stats']['accuracy_trend'].append({
                'date': datetime.now().isoformat(),
                'accuracy': round(recent_accuracy, 1),
                'sample_size': len(recent_predictions)
            })
            
            # שמור רק 30 נקודות מגמה
            if len(self.memory['learning_stats']['accuracy_trend']) > 30:
                self.memory['learning_stats']['accuracy_trend'] = self.memory['learning_stats']['accuracy_trend'][-30:]
    
    def get_model_performance(self) -> Dict:
        """קבל סטטיסטיקות ביצועים"""
        total = self.memory['learning_stats']['total_predictions']
        correct = self.memory['learning_stats']['correct_predictions']
        
        if total == 0:
            return {'overall_accuracy': 0, 'total_predictions': 0, 'trend': 'No data'}
        
        overall_accuracy = (correct / total) * 100
        
        # מגמה - משווים 10 האחרונים עם 10 לפני זה
        trend = 'Stable'
        if len(self.memory['learning_stats']['accuracy_trend']) >= 2:
            recent = self.memory['learning_stats']['accuracy_trend'][-1]['accuracy']
            older = self.memory['learning_stats']['accuracy_trend'][-2]['accuracy']
            
            if recent > older + 5:
                trend = 'Improving'
            elif recent < older - 5:
                trend = 'Declining'
        
        return {
            'overall_accuracy': round(overall_accuracy, 1),
            'total_predictions': total,
            'correct_predictions': correct,
            'trend': trend,
            'recent_accuracy': self.memory['learning_stats']['accuracy_trend'][-1]['accuracy'] if self.memory['learning_stats']['accuracy_trend'] else 0
        }
    
    def should_use_method(self, method: str) -> float:
        """קבע איזה משקל לתת לשיטה בהתבסס על ביצועים עבר"""
        method_predictions = [p for p in self.memory['predictions_log'] 
                            if p['method'] == method and p['verified']]
        
        if len(method_predictions) < 5:
            return 1.0  # ברירת מחדל לשיטות חדשות
        
        # חשב דיוק השיטה
        accurate_predictions = sum(1 for p in method_predictions if p['accuracy'] > 95)
        method_accuracy = accurate_predictions / len(method_predictions)
        
        # המר לגורם משקל (0.5 - 1.5)
        return max(0.5, min(1.5, method_accuracy * 1.5))
    
    def learn_from_patterns(self, symbol: str, market_data: pd.DataFrame) -> Dict:
        """למד דפוסי שוק מהנתונים"""
        patterns = {}
        
        if len(market_data) < 20:
            return patterns
        
        # דפוס 1: תנודתיות יומית ממוצעת
        daily_changes = market_data['Close'].pct_change().dropna()
        avg_volatility = daily_changes.std() * 100
        patterns['avg_volatility'] = round(avg_volatility, 2)
        
        # דפוס 2: מגמה אחרונה (10 ימים)
        recent_change = (market_data['Close'].iloc[-1] / market_data['Close'].iloc[-10] - 1) * 100
        patterns['recent_trend'] = round(recent_change, 2)
        
        # דפוס 3: תמיכה והתנגדות
        recent_high = market_data['High'].tail(20).max()
        recent_low = market_data['Low'].tail(20).min()
        current_position = (market_data['Close'].iloc[-1] - recent_low) / (recent_high - recent_low)
        patterns['position_in_range'] = round(current_position, 3)
        
        # שמור דפוסים
        if symbol not in self.memory['market_patterns']:
            self.memory['market_patterns'][symbol] = []
        
        pattern_entry = {
            'date': datetime.now().isoformat(),
            'patterns': patterns
        }
        
        self.memory['market_patterns'][symbol].append(pattern_entry)
        
        # שמור רק 50 דפוסים אחרונים לכל מניה
        if len(self.memory['market_patterns'][symbol]) > 50:
            self.memory['market_patterns'][symbol] = self.memory['market_patterns'][symbol][-50:]
        
        self.save_memory()
        return patterns

# יצירת instance גלובלי
model_memory = ModelMemory()