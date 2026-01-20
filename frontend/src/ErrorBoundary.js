import React from 'react';

/**
 * Error Boundary Component for Production
 * Catches JavaScript errors anywhere in the component tree
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0,
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console
    console.error('Error Boundary caught an error:', error, errorInfo);
    
    // Update state with error details
    this.setState(prevState => ({
      error,
      errorInfo,
      errorCount: prevState.errorCount + 1,
    }));

    // Log to error reporting service (if enabled)
    if (process.env.REACT_APP_ENABLE_ERROR_REPORTING === 'true') {
      this.logErrorToService(error, errorInfo);
    }

    // Attempt auto-recovery after 3 errors
    if (this.state.errorCount >= 3) {
      console.error('Too many errors. Reloading page...');
      setTimeout(() => window.location.reload(), 3000);
    }
  }

  logErrorToService = (error, errorInfo) => {
    // Send error to backend or external service
    try {
      const errorData = {
        message: error.toString(),
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
      };

      fetch(`${process.env.REACT_APP_API_URL}/api/errors/log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(errorData),
      }).catch(err => console.error('Failed to log error:', err));
    } catch (err) {
      console.error('Error logging failed:', err);
    }
  };

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0,
    });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      return (
        <div style={styles.container}>
          <div style={styles.errorBox}>
            <h1 style={styles.title}>⚠️ Something went wrong</h1>
            
            <p style={styles.description}>
              We apologize for the inconvenience. The application encountered an unexpected error.
            </p>

            <div style={styles.buttonGroup}>
              <button 
                onClick={this.handleReset} 
                style={styles.primaryButton}
              >
                Try Again
              </button>
              
              <button 
                onClick={this.handleReload} 
                style={styles.secondaryButton}
              >
                Reload Page
              </button>
            </div>

            {/* Show error details in development */}
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details style={styles.details}>
                <summary style={styles.summary}>Error Details (Dev Only)</summary>
                <pre style={styles.errorText}>
                  {this.state.error && this.state.error.toString()}
                  <br /><br />
                  {this.state.errorInfo && this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}

            <div style={styles.helpText}>
              <p>If the problem persists, please contact support.</p>
              <p style={styles.errorId}>
                Error ID: ERR-{Date.now()}
              </p>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Styles
const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    padding: '20px',
  },
  errorBox: {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '40px',
    maxWidth: '600px',
    width: '100%',
    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
  },
  title: {
    fontSize: '28px',
    fontWeight: 'bold',
    color: '#e53e3e',
    marginBottom: '16px',
    textAlign: 'center',
  },
  description: {
    fontSize: '16px',
    color: '#4a5568',
    marginBottom: '24px',
    textAlign: 'center',
    lineHeight: '1.6',
  },
  buttonGroup: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'center',
    marginBottom: '24px',
  },
  primaryButton: {
    backgroundColor: '#667eea',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.2s',
    boxShadow: '0 4px 6px rgba(102, 126, 234, 0.4)',
  },
  secondaryButton: {
    backgroundColor: '#e2e8f0',
    color: '#4a5568',
    border: 'none',
    borderRadius: '8px',
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  details: {
    marginTop: '24px',
    padding: '16px',
    backgroundColor: '#f7fafc',
    borderRadius: '8px',
    border: '1px solid #e2e8f0',
  },
  summary: {
    cursor: 'pointer',
    fontWeight: '600',
    color: '#4a5568',
    marginBottom: '12px',
  },
  errorText: {
    fontSize: '12px',
    color: '#e53e3e',
    overflow: 'auto',
    maxHeight: '200px',
    whiteSpace: 'pre-wrap',
    wordWrap: 'break-word',
  },
  helpText: {
    marginTop: '24px',
    textAlign: 'center',
    fontSize: '14px',
    color: '#718096',
  },
  errorId: {
    marginTop: '8px',
    fontSize: '12px',
    color: '#a0aec0',
    fontFamily: 'monospace',
  },
};

export default ErrorBoundary;
