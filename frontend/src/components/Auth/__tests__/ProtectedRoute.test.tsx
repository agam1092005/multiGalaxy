import React from 'react';
import { render, screen } from '@testing-library/react';
import { ProtectedRoute } from '../ProtectedRoute';
import { AuthProvider } from '../../../contexts/AuthContext';
import { apiService } from '../../../services/api';

// Mock the API service
jest.mock('../../../services/api');
const mockedApiService = apiService as jest.Mocked<typeof apiService>;

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

const TestComponent = () => <div>Protected Content</div>;

const MockedProtectedRoute = ({ children, requiredRole }: { children: React.ReactNode; requiredRole?: 'student' | 'parent' | 'teacher' }) => (
  <AuthProvider>
    <ProtectedRoute requiredRole={requiredRole}>
      {children}
    </ProtectedRoute>
  </AuthProvider>
);

describe('ProtectedRoute', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.getItem.mockReturnValue(null);
  });

  it('shows loading state initially', async () => {
    // Mock getCurrentUser to be slow so we can catch the loading state
    mockedApiService.getCurrentUser.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({
        id: '1',
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        role: 'student' as const,
        is_active: true,
        is_verified: true,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z'
      }), 100))
    );
    
    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'access_token') return 'fake-token';
      if (key === 'user') return JSON.stringify({
        id: '1',
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        role: 'student',
        is_active: true,
        is_verified: true,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z'
      });
      return null;
    });
    
    render(
      <MockedProtectedRoute>
        <TestComponent />
      </MockedProtectedRoute>
    );
    
    expect(screen.getByText('Loading...')).toBeInTheDocument();
    
    // Wait for loading to complete
    await screen.findByText('Protected Content');
  });

  it('shows auth page when user is not authenticated', async () => {
    mockLocalStorage.getItem.mockReturnValue(null);
    
    render(
      <MockedProtectedRoute>
        <TestComponent />
      </MockedProtectedRoute>
    );
    
    // Wait for loading to complete
    await screen.findByText('Multi-Galaxy-Note');
    expect(screen.getByText('Your AI-powered learning companion')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('shows protected content when user is authenticated', async () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      role: 'student' as const,
      is_active: true,
      is_verified: true,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z'
    };

    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'access_token') return 'fake-token';
      if (key === 'user') return JSON.stringify(mockUser);
      return null;
    });

    mockedApiService.getCurrentUser.mockResolvedValue(mockUser);
    
    render(
      <MockedProtectedRoute>
        <TestComponent />
      </MockedProtectedRoute>
    );
    
    await screen.findByText('Protected Content');
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('shows access denied when user role does not match required role', async () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      role: 'student' as const,
      is_active: true,
      is_verified: true,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z'
    };

    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'access_token') return 'fake-token';
      if (key === 'user') return JSON.stringify(mockUser);
      return null;
    });

    mockedApiService.getCurrentUser.mockResolvedValue(mockUser);
    
    render(
      <MockedProtectedRoute requiredRole="teacher">
        <TestComponent />
      </MockedProtectedRoute>
    );
    
    await screen.findByText('Access Denied');
    expect(screen.getByText('Access Denied')).toBeInTheDocument();
    expect(screen.getByText('Required role: teacher, Your role: student')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('shows protected content when user role matches required role', async () => {
    const mockUser = {
      id: '1',
      email: 'teacher@example.com',
      first_name: 'Test',
      last_name: 'Teacher',
      role: 'teacher' as const,
      is_active: true,
      is_verified: true,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z'
    };

    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'access_token') return 'fake-token';
      if (key === 'user') return JSON.stringify(mockUser);
      return null;
    });

    mockedApiService.getCurrentUser.mockResolvedValue(mockUser);
    
    render(
      <MockedProtectedRoute requiredRole="teacher">
        <TestComponent />
      </MockedProtectedRoute>
    );
    
    await screen.findByText('Protected Content');
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });
});