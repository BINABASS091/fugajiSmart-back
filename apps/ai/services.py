"""
FugajiBot AI Service
Handles OpenAI integration and context injection for personalized farming advice.
"""
import os
import time
from typing import Dict, List, Optional
from openai import OpenAI
from django.conf import settings
from apps.consolidated.models import Batch, Alert, FarmerProfile


class FugajiBotService:
    """
    Service class for FugajiBot AI assistant.
    Integrates with OpenAI and injects farm-specific context.
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY', ''))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    
    def get_farm_context(self, user) -> Dict:
        """
        Gather relevant farm data to inject into AI prompts.
        """
        context = {
            'farmer_name': user.get_full_name() or user.email,
            'batches': [],
            'alerts': [],
            'total_birds': 0
        }
        
        try:
            # Get farmer profile
            if hasattr(user, 'farmer_profile'):
                profile = user.farmer_profile
                context['business_name'] = profile.business_name
                context['location'] = profile.location
                
                # Get active batches
                batches = Batch.objects.filter(
                    farm__farmer=profile,
                    status='ACTIVE'
                ).select_related('farm')[:5]
                
                for batch in batches:
                    context['batches'].append({
                        'breed': batch.breed,
                        'age_days': (time.time() - batch.start_date.timestamp()) // 86400 if batch.start_date else 0,
                        'initial_count': batch.initial_count,
                        'current_count': batch.current_count,
                        'mortality_rate': batch.mortality_rate
                    })
                    context['total_birds'] += batch.current_count or 0
                
                # Get recent alerts
                alerts = Alert.objects.filter(
                    farmer=profile,
                    is_read=False
                ).order_by('-created_at')[:3]
                
                for alert in alerts:
                    context['alerts'].append({
                        'type': alert.alert_type,
                        'severity': alert.severity,
                        'message': alert.message
                    })
        
        except Exception as e:
            print(f"Error gathering farm context: {e}")
        
        return context
    
    def build_system_prompt(self, context: Dict, language: str = 'sw') -> str:
        """
        Build the system prompt with farm context.
        """
        if language == 'sw':
            prompt = f"""Wewe ni FugajiBot, msaidizi wa AI wa wafugaji wa kuku nchini Tanzania. 
Jibu kwa Kiswahili kwa kawaida, lakini unaweza kutumia Kiingereza ikiwa mtumiaji anaomba.

MUKTADHA WA SHAMBA:
- Mfugaji: {context.get('farmer_name', 'Mfugaji')}
- Jina la Biashara: {context.get('business_name', 'Hakuna')}
- Mahali: {context.get('location', 'Tanzania')}
- Idadi ya Kuku: {context.get('total_birds', 0)}
- Makundi Hai: {len(context.get('batches', []))}

MAKUNDI:
{self._format_batches_sw(context.get('batches', []))}

TAHADHARI ZA SASA:
{self._format_alerts_sw(context.get('alerts', []))}

MIONGOZO:
1. Toa ushauri wa vitendo na wa kiufundi
2. Rejelea aina za kuku za Tanzania (Kuroiler, Sasso, Broiler, Layers)
3. Zingatia hali ya hewa ya Tanzania na chakula kinachopatikana
4. Kuwa mfupi lakini kamili
5. Ikiwa unaulizwa kuhusu data maalum ya shamba, tumia MUKTADHA hapo juu
6. Ikiwa huna uhakika, pendekeza kuwasiliana na daktari wa wanyama

MIFANO YA MASWALI:
- "Kuku wangu wana harara, nifanye nini?" → Tambua na pendekeza matibabu
- "Chakula cha kuku wa wiki 3 ni kiasi gani?" → Toa mwongozo wa kulisha
- "Joto ni juu sana, nifanye nini?" → Ushauri wa kudhibiti mazingira
"""
        else:  # English
            prompt = f"""You are FugajiBot, an AI assistant for poultry farmers in Tanzania.
Respond primarily in English, but can use Swahili if requested.

FARM CONTEXT:
- Farmer: {context.get('farmer_name', 'Farmer')}
- Business Name: {context.get('business_name', 'N/A')}
- Location: {context.get('location', 'Tanzania')}
- Total Birds: {context.get('total_birds', 0)}
- Active Batches: {len(context.get('batches', []))}

BATCHES:
{self._format_batches_en(context.get('batches', []))}

CURRENT ALERTS:
{self._format_alerts_en(context.get('alerts', []))}

GUIDELINES:
1. Provide practical, actionable advice
2. Reference local breeds (Kuroiler, Sasso, Broiler, Layers)
3. Consider Tanzanian climate and feed availability
4. Be concise but thorough
5. If asked about specific farm data, use the CONTEXT above
6. If uncertain, recommend consulting a veterinarian

EXAMPLE QUERIES:
- "My chickens have diarrhea, what should I do?" → Diagnose and recommend treatment
- "How much feed for 3-week-old broilers?" → Provide feeding guidelines
- "Temperature is too high, what to do?" → Environmental control advice
"""
        
        return prompt
    
    def _format_batches_sw(self, batches: List[Dict]) -> str:
        if not batches:
            return "Hakuna makundi hai kwa sasa"
        
        formatted = []
        for i, batch in enumerate(batches, 1):
            formatted.append(
                f"{i}. {batch['breed']} - Umri: siku {batch.get('age_days', 0)}, "
                f"Idadi: {batch.get('current_count', 0)}/{batch.get('initial_count', 0)}, "
                f"Vifo: {batch.get('mortality_rate', 0):.1f}%"
            )
        return "\n".join(formatted)
    
    def _format_batches_en(self, batches: List[Dict]) -> str:
        if not batches:
            return "No active batches currently"
        
        formatted = []
        for i, batch in enumerate(batches, 1):
            formatted.append(
                f"{i}. {batch['breed']} - Age: {batch.get('age_days', 0)} days, "
                f"Count: {batch.get('current_count', 0)}/{batch.get('initial_count', 0)}, "
                f"Mortality: {batch.get('mortality_rate', 0):.1f}%"
            )
        return "\n".join(formatted)
    
    def _format_alerts_sw(self, alerts: List[Dict]) -> str:
        if not alerts:
            return "Hakuna tahadhari za sasa"
        
        formatted = []
        for alert in alerts:
            formatted.append(f"- [{alert['severity']}] {alert['message']}")
        return "\n".join(formatted)
    
    def _format_alerts_en(self, alerts: List[Dict]) -> str:
        if not alerts:
            return "No current alerts"
        
        formatted = []
        for alert in alerts:
            formatted.append(f"- [{alert['severity']}] {alert['message']}")
        return "\n".join(formatted)
    
    def generate_response(
        self,
        user_message: str,
        conversation_history: List[Dict],
        user,
        language: str = 'sw'
    ) -> Dict:
        """
        Generate AI response using OpenAI.
        
        Returns:
            {
                'response': str,
                'model_used': str,
                'tokens_used': int,
                'response_time_ms': int,
                'suggestions': List[str]
            }
        """
        start_time = time.time()
        
        try:
            # Get farm context
            context = self.get_farm_context(user)
            
            # Build system prompt
            system_prompt = self.build_system_prompt(context, language)
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add conversation history (last 10 messages)
            messages.extend(conversation_history[-10:])
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Call OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            # Extract response
            ai_response = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            # Generate suggestions
            suggestions = self._generate_suggestions(user_message, language)
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                'response': ai_response,
                'model_used': self.model,
                'tokens_used': tokens_used,
                'response_time_ms': response_time_ms,
                'suggestions': suggestions,
                'context_used': context
            }
        
        except Exception as e:
            print(f"Error generating AI response: {e}")
            
            # Fallback response
            if language == 'sw':
                fallback = "Samahani, nimepata tatizo la kiufundi. Tafadhali jaribu tena au wasiliana na msaada."
            else:
                fallback = "Sorry, I encountered a technical issue. Please try again or contact support."
            
            return {
                'response': fallback,
                'model_used': 'fallback',
                'tokens_used': 0,
                'response_time_ms': int((time.time() - start_time) * 1000),
                'suggestions': [],
                'context_used': {}
            }
    
    def _generate_suggestions(self, user_message: str, language: str) -> List[str]:
        """
        Generate follow-up question suggestions based on the user's query.
        """
        if language == 'sw':
            suggestions = [
                "Niambie zaidi kuhusu hali ya shamba langu",
                "Je, kuna tahadhari zozote za sasa?",
                "Nisaidie kupanga ratiba ya chanjo"
            ]
        else:
            suggestions = [
                "Tell me more about my farm status",
                "Are there any current alerts?",
                "Help me plan vaccination schedule"
            ]
        
        return suggestions[:3]  # Return top 3
