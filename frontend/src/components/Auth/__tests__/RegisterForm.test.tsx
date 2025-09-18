import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RegisterForm } from '../RegisterForm';
import { AuthProvider } from '../../../contexts/AuthContext';
import { apiService } from '../../../services/api';

// Mock the API service
jest.mock('../../../services/api');
const mockedApiService = apiService as jest.Mocked<typeof apiService>;

// Mock component with AuthProvider
const MockedRegisterForm = (props: any) => (
  <AuthProvider>
    <RegisterForm {...props} />
  </AuthProvider>
);

describe('RegisterForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders register form correctly', () => {
    render(<MockedRegisterForm />);
    
    expect(screen.getByRole('heading', { name: 'Create Account' })).toBeInTheDocument();
    expect(screen.getByLabelText('First Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Last Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByLabelText('Role')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create Account' })).toBeInTheDocument();
  });

  it('handles form input changes', async () => {
    render(<MockedRegisterForm />);
    
    const firstNameInput = screen.getByLabelText('First Name');
    const lastNameInput = screen.getByLabelText('Last Name');
    const emailInput = screen.getByLabelText('Email');
    const passwordInput = screen.getByLabelText('Password');
    const roleSelect = screen.getByLabelText('Role');
    
    await userEvent.type(firstNameInput, 'John');
    await userEvent.type(lastNameInput, 'Doe');
    await userEvent.type(emailInput, 'john@example.com');
    await userEvent.type(passwordInput, 'Password123');
    await userEvent.selectOptions(roleSelect, 'teacher');
    
    expect(firstNameInput).toHaveValue('John');
    expect(lastNameInput).toHaveValue('Doe');
    expect(emailInput).toHaveValue('john@example.com');
    expect(passwordInput).toHaveValue('Password123');
    expect(roleSelect).toHaveValue('teacher');
  });

  it('calls onSuccess when registration is successful', async () => {
    const mockOnSuccess = jest.fn();
    
    // Mock successful registration and login
    mockedApiService.register.mockResolvedValue({
      id: '1',
      email: 'john@example.com',
      first_name: 'John',
      last_name: 'Doe',
      role: 'student',
      is_active: true,
      is_verified: false,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z'
    });
    
    mockedApiService.login.mockResolvedValue({
      access_token: 'fake-token',
      token_type: 'bearer',
      expires_in: 3600,
      user: {
        id: '1',
        email: 'john@example.com',
        first_name: 'John',
        last_name: 'Doe',
        role: 'student',
        is_active: true,
        is_verified: false,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z'
      }
    });
    
    render(<MockedRegisterForm onSuccess={mockOnSuccess} />);
    
    await userEvent.type(screen.getByLabelText('First Name'), 'John');
    await userEvent.type(screen.getByLabelText('Last Name'), 'Doe');
    await userEvent.type(screen.getByLabelText('Email'), 'john@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'Password123');
    await userEvent.click(screen.getByRole('button', { name: 'Create Account' }));
    
    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled();
    });
  });

  it('displays error message when registration fails', async () => {
    mockedApiService.register.mockRejectedValue({
      response: {
        data: {
          detail: 'Email already registered'
        }
      }
    });
    
    render(<MockedRegisterForm />);
    
    await userEvent.type(screen.getByLabelText('First Name'), 'John');
    await userEvent.type(screen.getByLabelText('Last Name'), 'Doe');
    await userEvent.type(screen.getByLabelText('Email'), 'existing@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'Password123');
    await userEvent.click(screen.getByRole('button', { name: 'Create Account' }));
    
    await waitFor(() => {
      expect(screen.getByText('Email already registered')).toBeInTheDocument();
    });
  });

  it('shows loading state during registration', async () => {
    // Mock a delayed response
    mockedApiService.register.mockImplementation(() => 
      new Promise(resolve => setTimeout(resolve, 100))
    );
    
    render(<MockedRegisterForm />);
    
    await userEvent.type(screen.getByLabelText('First Name'), 'John');
    await userEvent.type(screen.getByLabelText('Last Name'), 'Doe');
    await userEvent.type(screen.getByLabelText('Email'), 'john@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'Password123');
    await userEvent.click(screen.getByRole('button', { name: 'Create Account' }));
    
    expect(screen.getByText('Creating Account...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Creating Account...' })).toBeDisabled();
  });

  it('calls onSwitchToLogin when login link is clicked', async () => {
    const mockOnSwitchToLogin = jest.fn();
    
    render(<MockedRegisterForm onSwitchToLogin={mockOnSwitchToLogin} />);
    
    await userEvent.click(screen.getByText('Sign in'));
    
    expect(mockOnSwitchToLogin).toHaveBeenCalled();
  });
});