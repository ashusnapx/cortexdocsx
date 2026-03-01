"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className='min-h-[400px] flex flex-col items-center justify-center p-6 text-center'>
          <div className='w-16 h-16 bg-error rounded-2xl flex items-center justify-center mb-6'>
            <AlertTriangle className='w-8 h-8 text-errorForeground' />
          </div>
          <h2 className='text-2xl font-semibold text-foreground mb-3 tracking-tight'>
            Something went wrong
          </h2>
          <p className='text-muted max-w-md mb-8'>
            {this.state.error?.message ||
              "An unexpected error occurred in this component."}
          </p>
          <button
            onClick={() => this.setState({ hasError: false })}
            className='px-6 py-3 bg-primary text-white rounded-full font-medium hover:bg-primaryHover transition-colors duration-200'
          >
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
