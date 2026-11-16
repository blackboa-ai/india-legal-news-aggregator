import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AuthModal } from '../components/AuthModal';
import { AuthProvider } from '../context/AuthContext';

describe('AuthModal Component', () => {
  const renderWithAuth = (ui: React.ReactElement) => {
    return render(<AuthProvider>{ui}</AuthProvider>);
  };

  it('renders login tab by default with email and password inputs', () => {
    renderWithAuth(<AuthModal isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Sign in to Legal Workspace')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('counsel@lawchamber.in')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/min 6 characters/i)).toBeInTheDocument();
    expect(screen.getByText('Sign in with Google')).toBeInTheDocument();
  });

  it('switches to register tab when Create Account is clicked', () => {
    renderWithAuth(<AuthModal isOpen={true} onClose={vi.fn()} />);

    const createTab = screen.getByText('Create Account');
    fireEvent.click(createTab);

    expect(screen.getByText('Create Free Account')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Adv. Vikram Mehta')).toBeInTheDocument();
  });

  it('does not render when isOpen is false', () => {
    const { container } = renderWithAuth(<AuthModal isOpen={false} onClose={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });
});
