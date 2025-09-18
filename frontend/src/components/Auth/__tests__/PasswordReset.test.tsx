import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { apiService } from '../../../services/api';

// Mock the API service
jest.mock('../../../services/api');
const mockedApiService = apiService as jest.Mocked<typeof apiService>;

// Simple password reset component for testing
const PasswordResetForm: React.FC = () => {
  const [email, setEmail] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [message, setMessage] = React.useState('');
  const [error, setError] = React.useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');

    try {
      await apiService.requestPasswordReset({ email });
      setMessage('If the email exists, a password reset link has been sent');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send reset email');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h2>Reset Password</h2>
      {error && <div role="alert">{error}</div>}
      {message && <div>{message}</div>}
      <label htmlFor="email">Email</label>
      <input
        type="email"
        id="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Sending...' : 'Send Reset Link'}
      </button>
    </form>
  );
};

describe('PasswordResetForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders password reset form correctly', () => {
    render(<PasswordResetForm />);
    
    expect(screen.getByRole('heading', { name: 'Reset Password' })).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Send Reset Link' })).toBeInTheDocument();
  });

  it('handles form submission successfully', async () => {
    mockedApiService.requestPasswordReset.mockResolvedValue();
    
    render(<PasswordResetForm />);
    
    await userEvent.type(screen.getByLabelText('Email'), 'test@example.com');
    await userEvent.click(screen.getByRole('button', { name: 'Send Reset Link' }));
    
    await waitFor(() => {
      expect(screen.getByText('If the email exists, a password reset link has been sent')).toBeInTheDocument();
    });
    
    expect(mockedApiService.requestPasswordReset).toHaveBeenCalledWith({
      email: 'test@example.com'
    });
  });

  it('displays error message when request fails', async () => {
    mockedApiService.requestPasswordReset.mockRejectedValue({
      response: {
        data: {
          detail: 'Service unavailable'
        }
      }
    });
    
    render(<PasswordResetForm />);
    
    await userEvent.type(screen.getByLabelText('Email'), 'test@example.com');
    await userEvent.click(screen.getByRole('button', { name: 'Send Reset Link' }));
    
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Service unavailable');
    });
  });

  it('shows loading state during submission', async () => {
    mockedApiService.requestPasswordReset.mockImplementation(() => 
      new Promise(resolve => setTimeout(resolve, 100))
    );
    
    render(<PasswordResetForm />);
    
    await userEvent.type(screen.getByLabelText('Email'), 'test@example.com');
    await userEvent.click(screen.getByRole('button', { name: 'Send Reset Link' }));
    
    expect(screen.getByText('Sending...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sending...' })).toBeDisabled();
  });
});