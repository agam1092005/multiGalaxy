import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders Multi-Galaxy-Note app', () => {
  render(<App />);
  const titleElement = screen.getByText('Multi-Galaxy-Note');
  expect(titleElement).toBeInTheDocument();
  
  const subtitleElement = screen.getByText('Your AI-powered learning companion');
  expect(subtitleElement).toBeInTheDocument();
});
