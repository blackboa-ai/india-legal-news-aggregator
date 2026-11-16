import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FeedbackModal, FloatingFeedbackButton } from '../components/FeedbackModal';
import { AuthProvider } from '../context/AuthContext';
import { api } from '../api/client';

describe('FloatingFeedbackButton Component', () => {
  it('renders correctly and calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<FloatingFeedbackButton onClick={handleClick} />);

    const button = screen.getByRole('button', { name: /give feedback/i });
    expect(button).toBeInTheDocument();
    expect(screen.getByText('Feedback')).toBeInTheDocument();

    fireEvent.click(button);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});

describe('FeedbackModal Component', () => {
  const renderWithAuth = (ui: React.ReactElement) => {
    return render(<AuthProvider>{ui}</AuthProvider>);
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when isOpen is false', () => {
    const { container } = renderWithAuth(
      <FeedbackModal isOpen={false} onClose={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders private modal without tabs and displays rating stars, category selector, textarea and submit button', () => {
    renderWithAuth(<FeedbackModal isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Feedback & Reviews')).toBeInTheDocument();
    expect(screen.getByText(/How was your experience/i)).toBeInTheDocument();

    // Verify tabs are NOT present
    expect(screen.queryByRole('button', { name: /recent feedback & stats/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/recent feedback & stats/i)).not.toBeInTheDocument();

    // 5 star buttons
    expect(screen.getByRole('button', { name: /rate 1 out of 5 stars/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /rate 5 out of 5 stars/i })).toBeInTheDocument();

    // Category options
    expect(screen.getByRole('button', { name: 'General' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Feature Request' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Bug Report' })).toBeInTheDocument();

    // Textarea & Email
    expect(screen.getByPlaceholderText(/Tell us what you like/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/your.email@example.com/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send feedback/i })).toBeInTheDocument();
  });

  it('updates selected rating and label on star click', () => {
    renderWithAuth(<FeedbackModal isOpen={true} onClose={vi.fn()} />);

    const star3 = screen.getByRole('button', { name: /rate 3 out of 5 stars/i });
    fireEvent.click(star3);

    expect(screen.getByText(/Good — Useful for legal research/i)).toBeInTheDocument();
  });

  it('submits feedback via api and displays thank you screen without View All Feedback button', async () => {
    const mockSubmit = vi.spyOn(api.feedback, 'submit').mockResolvedValueOnce({
      id: 'test-feedback-uuid',
      rating: 5,
      feedback_text: 'The case headnotes and citations are extremely accurate.',
      email: 'counsel@chamber.in',
      category: 'general',
      user_id: null,
      created_at: new Date().toISOString(),
    });

    renderWithAuth(<FeedbackModal isOpen={true} onClose={vi.fn()} />);

    const textarea = screen.getByPlaceholderText(/Tell us what you like/i);
    fireEvent.change(textarea, {
      target: { value: 'The case headnotes and citations are extremely accurate.' },
    });

    const emailInput = screen.getByPlaceholderText(/your.email@example.com/i);
    fireEvent.change(emailInput, { target: { value: 'counsel@chamber.in' } });

    const submitBtn = screen.getByRole('button', { name: /send feedback/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledTimes(1);
      expect(mockSubmit).toHaveBeenCalledWith({
        rating: 5,
        feedback_text: 'The case headnotes and citations are extremely accurate.',
        email: 'counsel@chamber.in',
        category: 'general',
      });
    });

    expect(await screen.findByText('Thank You!')).toBeInTheDocument();
    expect(
      screen.getByText(/Your feedback has been successfully recorded in the database/i)
    ).toBeInTheDocument();

    // Buttons on success screen: Submit Another Review and Close, but NO "View All Feedback"
    expect(screen.getByRole('button', { name: /submit another review/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^close$/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /view all feedback/i })).not.toBeInTheDocument();
  });

  it('calls onClose when Close button is clicked on thank you screen', async () => {
    const handleClose = vi.fn();
    vi.spyOn(api.feedback, 'submit').mockResolvedValueOnce({
      id: 'test-feedback-uuid-2',
      rating: 4,
      feedback_text: 'Very helpful research tool.',
      email: undefined,
      category: 'general',
      user_id: null,
      created_at: new Date().toISOString(),
    });

    renderWithAuth(<FeedbackModal isOpen={true} onClose={handleClose} />);

    fireEvent.change(screen.getByPlaceholderText(/Tell us what you like/i), {
      target: { value: 'Very helpful research tool.' },
    });
    fireEvent.click(screen.getByRole('button', { name: /send feedback/i }));

    const closeBtn = await screen.findByRole('button', { name: /^close$/i });
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
