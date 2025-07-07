import React from 'react';
import { render, screen } from '@testing-library/react';
// import ExecutiveSummaryCard from './ExecutiveSummaryCard'; // Assuming this component would exist

// Mock a simple ExecutiveSummaryCard component for the test to run conceptually
const ExecutiveSummaryCard = ({ title, value, trend }: { title: string, value: string, trend?: string }) => {
  return (
    <div data-testid="executive-summary-card">
      <h3>{title}</h3>
      <p>{value}</p>
      {trend && <small>Trend: {trend}</small>}
    </div>
  );
};

describe('ExecutiveSummaryCard Component', () => {
  test('renders with title and value', () => {
    render(<ExecutiveSummaryCard title="Total Revenue" value="$150,000" />);

    const titleElement = screen.getByText(/Total Revenue/i);
    const valueElement = screen.getByText(/\$150,000/i);

    expect(titleElement).toBeInTheDocument();
    expect(valueElement).toBeInTheDocument();
  });

  test('renders trend if provided', () => {
    render(<ExecutiveSummaryCard title="New Customers" value="120" trend="+5%" />);

    const trendElement = screen.getByText(/Trend: \+5%/i);
    expect(trendElement).toBeInTheDocument();
  });

  test('does not render trend if not provided', () => {
    render(<ExecutiveSummaryCard title="Active Users" value="1,200" />);

    const trendElement = screen.queryByText(/Trend:/i);
    expect(trendElement).not.toBeInTheDocument();
  });

  test('matches snapshot', () => {
    const { container } = render(<ExecutiveSummaryCard title="Conversion Rate" value="2.5%" trend="-0.1%" />);
    expect(container.firstChild).toMatchSnapshot();
  });
});

// To run this test (conceptual, as part of a React project):
// 1. Ensure you have @testing-library/react, @testing-library/jest-dom, and jest configured.
// 2. Place this file in the appropriate components directory (e.g., src/components/Dashboard/).
// 3. Run your test script (e.g., `npm test` or `yarn test`).
//
// This file includes a mock implementation of ExecutiveSummaryCard directly within it
// for demonstration purposes, as the actual component doesn't exist.
// In a real scenario, you would import the actual component.
