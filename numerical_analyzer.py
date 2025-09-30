import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

class NumericalAnalyzer:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.data = pd.read_csv(csv_path)
    
    def get_data_summary(self):
        """Get a summary of the dataset"""
        summary = {
            "total_rows": len(self.data),
            "columns": list(self.data.columns),
            "numeric_columns": list(self.data.select_dtypes(include=[np.number]).columns),
            "categorical_columns": list(self.data.select_dtypes(include=['object']).columns)
        }
        return summary
    
    def comprehensive_analysis(self, question):
        """Perform comprehensive analysis using direct calculations"""
        try:
            # Get data summary
            data_summary = self.get_data_summary()
            
            # Perform direct statistical analysis
            stats = {
                'total_records': len(self.data),
                'total_quantity': self.data['quantity'].sum(),
                'total_revenue': (self.data['rate'] * self.data['quantity']).sum(),
                'average_rate': self.data['rate'].mean(),
                'average_quantity': self.data['quantity'].mean(),
                'unique_agents': self.data['agentName'].nunique(),
                'unique_customers': self.data['customerName'].nunique()
            }
            
            # Generate comprehensive response
            response = f"""
📊 COMPREHENSIVE DATA ANALYSIS:

📈 KEY STATISTICS:
• Total Records: {stats['total_records']}
• Total Quantity: {stats['total_quantity']:,.2f}
• Total Revenue: ${stats['total_revenue']:,.2f}
• Average Rate: ${stats['average_rate']:.2f}
• Average Quantity: {stats['average_quantity']:,.2f}
• Unique Agents: {stats['unique_agents']}
• Unique Customers: {stats['unique_customers']}

📋 DATA SUMMARY:
• Columns: {', '.join(data_summary['columns'])}
• Numeric Columns: {', '.join(data_summary['numeric_columns'])}
• Categorical Columns: {', '.join(data_summary['categorical_columns'])}
"""
            
            # Add basic statistical analysis if applicable
            stats_analysis = self._generate_basic_stats(question)
            
            if stats_analysis:
                response += f"\n📊 SPECIFIC CALCULATIONS:\n{stats_analysis}"
                
            return response
            
        except Exception as e:
            return f"❌ Analysis failed: {str(e)}\n\nFalling back to basic data summary:\n{self.get_data_summary()}"
    
    def _generate_basic_stats(self, question):
        """Generate basic statistics based on the question"""
        try:
            stats = []
            question_lower = question.lower()
            
            # Check for agent-specific queries
            if 'agent' in question_lower and any(agent in question_lower for agent in ['mukilan', 'devaraj', 'boopalan']):
                for agent in ['mukilan', 'devaraj', 'boopalan']:
                    if agent in question_lower:
                        agent_data = self.data[self.data['agentName'].str.lower() == agent.lower()]
                        # Check for specific status in the question
                        if 'confirmed orders' in question_lower:
                            agent_data = agent_data[agent_data['status'] == 'Confirmed']
                        elif 'declined orders' in question_lower:
                            agent_data = agent_data[agent_data['status'] == 'Declined']
                        elif 'pending orders' in question_lower:
                            agent_data = agent_data[agent_data['status'] == 'Pending']
                        
                        record_count = len(agent_data)
                        status_text = ''
                        if 'confirmed orders' in question_lower:
                            status_text = 'confirmed'
                        elif 'declined orders' in question_lower:
                            status_text = 'declined'
                        elif 'pending orders' in question_lower:
                            status_text = 'pending'
                        else:
                            status_text = 'total'
                        stats.append(f"{agent.title()} has {record_count} {status_text} orders")
                        break
            
            # Check for common statistical keywords
            elif any(word in question_lower for word in ['total', 'sum']):
                numeric_cols = self.data.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    total = self.data[col].sum()
                    stats.append(f"Total {col}: {total:,.2f}")
            
            elif any(word in question_lower for word in ['average', 'mean']):
                numeric_cols = self.data.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    mean_val = self.data[col].mean()
                    stats.append(f"Average {col}: {mean_val:.2f}")
            
            elif any(word in question_lower for word in ['count', 'how many']):
                stats.append(f"Total records: {len(self.data)}")
                for col in self.data.columns:
                    unique_count = self.data[col].nunique()
                    stats.append(f"Unique {col} values: {unique_count}")
            
            elif any(word in question_lower for word in ['maximum', 'highest']):
                numeric_cols = self.data.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    max_val = self.data[col].max()
                    stats.append(f"Maximum {col}: {max_val:,.2f}")
            
            elif any(word in question_lower for word in ['minimum', 'lowest']):
                numeric_cols = self.data.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    min_val = self.data[col].min()
                    stats.append(f"Minimum {col}: {min_val:,.2f}")
            
            return "\n".join(stats) if stats else None
            
        except Exception as e:
            return f"❌ Statistics calculation failed: {str(e)}"

def create_numerical_analyzer(csv_path):
    """Factory function to create a numerical analyzer"""
    return NumericalAnalyzer(csv_path)
