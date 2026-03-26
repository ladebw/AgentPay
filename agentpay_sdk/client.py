"""Main client for interacting with the AgentPay API."""
import json
from typing import Dict, Any, Optional
import requests
from .exceptions import AuthenticationError, APIError, NotFoundError, RateLimitError, ValidationError


class AgentPayClient:
    """Client for the AgentPay API."""
    
    def __init__(self, base_url: str, api_key: str):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of the AgentPay API (e.g., "https://api.agentpay.example.com")
            api_key: Your API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': f'AgentPay SDK 0.1.0',
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request to the API."""
        url = f'{self.base_url}{endpoint}'
        try:
            response = self.session.request(method, url, **kwargs)
        except requests.exceptions.RequestException as e:
            raise APIError(f"Network error: {e}")
        
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        elif response.status_code == 404:
            raise NotFoundError(f"Resource not found: {endpoint}")
        elif response.status_code == 422:
            raise ValidationError(f"Validation error: {response.text}")
        elif response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        elif response.status_code >= 400:
            raise APIError(
                f"API error {response.status_code}: {response.text}",
                status_code=response.status_code,
                response=response
            )
        
        # Successful response
        if response.status_code == 204:
            return {}
        try:
            return response.json()
        except json.JSONDecodeError:
            raise APIError(f"Invalid JSON response: {response.text}")
    
    # Agent endpoints
    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Retrieve an agent by ID."""
        return self._request('GET', f'/agents/{agent_id}')
    
    def create_agent(self, wallet_address: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new agent."""
        payload = {
            'wallet_address': wallet_address,
        }
        if name:
            payload['name'] = name
        return self._request('POST', '/agents', json=payload)
    
    # Invoice endpoints
    def create_invoice(
        self,
        to_agent_id: str,
        amount: float,
        currency: str = 'USDC',
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new invoice."""
        payload = {
            'to_agent_id': to_agent_id,
            'amount': amount,
            'currency': currency,
        }
        if description:
            payload['description'] = description
        return self._request('POST', '/invoices', json=payload)
    
    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Retrieve an invoice by ID."""
        return self._request('GET', f'/invoices/{invoice_id}')
    
    # Payment endpoints
    def pay_invoice(self, invoice_id: str, from_agent_id: str) -> Dict[str, Any]:
        """Pay an invoice."""
        payload = {
            'from_agent_id': from_agent_id,
        }
        return self._request('POST', f'/invoices/{invoice_id}/pay', json=payload)
    
    def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """Retrieve a payment by ID."""
        return self._request('GET', f'/payments/{payment_id}')
    
    # Wallet endpoints
    def get_wallet(self, agent_id: str) -> Dict[str, Any]:
        """Retrieve wallet details for an agent."""
        return self._request('GET', f'/agents/{agent_id}/wallet')
    
    # Gas sponsorship endpoints
    def request_gas_sponsorship(
        self,
        agent_id: str,
        transaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Request gas sponsorship for a transaction."""
        payload = {
            'agent_id': agent_id,
            'transaction_data': transaction_data,
        }
        return self._request('POST', '/sponsor/request', json=payload)
    
    # Utility methods
    def health(self) -> Dict[str, Any]:
        """Check API health."""
        return self._request('GET', '/health')