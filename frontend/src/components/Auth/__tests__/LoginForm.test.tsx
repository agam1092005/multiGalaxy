import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginForm } from '../LoginForm';
import { AuthProvider } from '../../../contexts/AuthContext';
import { apiService } from '../../../services/api';

// Mock the API service
jest.mock('../../../services/api');
const mockedApiService = apiService as jest.Mocked<typeof apiService>;

// Mock component with AuthProvider
const MockedLoginForm = (props: any) => (
  <AuthProvider>
    <LoginForm {...props} />
  </AuthProvider>
);

describe('LoginForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders login form correctly', () => {
    render(<MockedLoginForm />);
    
    expect(screen.getByRole('heading', { name: 'Sign In' })).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDocument();
  });

  it('handles form input changes', async () => {
    render(<MockedLoginForm />);
    
    const emailInput = screen.getByLabelText('Email');
    const passwordInput = screen.getByLabelText('Password');
    
    await userEvent.type(emailInput, 'test@example.com');
    await userEvent.type(passwordInput, 'password123');
    
    expect(emailInput).toHaveValue('test@example.com');
    expect(passwordInput).toHaveValue('password123');
  });

  it('calls onSuccess when login is successful', async () => {
    const mockOnSuccess = jest.fn();
    
    mockedApiService.login.mockResolvedValue({
      access_token: 'fake-token',
      token_type: 'bearer',
      expires_in: 3600,
      user: {
        id: '1',
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        role: 'student',
        is_active: true,
        is_verified: true,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z'
      }
    });
    
    render(<MockedLoginForm onSuccess={mockOnSuccess} />);
    
    await userEvent.type(screen.getByLabelText('Email'), 'test@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'password123');
    await userEvent.click(screen.getByRole('button', { name: 'Sign In' }));
    
    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled();
    });
  });

  it('displays error message when login fails', async () => {
    mockedApiService.login.mockRejectedValue({
      response: {
        data: {
          detail: 'Incorrect email or password'
        }
      }
    });
    
    render(<MockedLoginForm />);
    
    await userEvent.type(screen.getByLabelText('Email'), 'test@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'wrongpassword');
    await userEvent.click(screen.getByRole('button', { name: 'Sign In' }));
    
    await waitFor(() => {
      expect(screen.getByText('Incorrect email or password')).toBeInTheDocument();
    });
  });

  it('shows loading state during login', async () => {
    // Mock a delayed response
    mockedApiService.login.mockImplementation(() => 
      new Promise(resolve => setTimeout(resolve, 100))
    );
    
    render(<MockedLoginForm />);
    
    await userEvent.type(screen.getByLabelText('Email'), 'test@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'password123');
    await userEvent.click(screen.getByRole('button', { name: 'Sign In' }));
    
    expect(screen.getByText('Signing In...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Signing In...' })).toBeDisabled();
  });

  it('calls onSwitchToRegister when register link is clicked', async () => {
    const mockOnSwitchToRegister = jest.fn();
    
    render(<MockedLoginForm onSwitchToRegister={mockOnSwitchToRegister} />);
    
    await userEvent.click(screen.getByText('Sign up'));
    
    expect(mockOnSwitchToRegister).toHaveBeenCalled();
  });
});