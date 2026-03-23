import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { TrendingUp, Mail, ArrowLeft, AlertCircle, CheckCircle } from 'lucide-react';
import { Input, Button } from '@/components/ui';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [resetToken, setResetToken] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        const data = await response.json();
        setSuccess(true);
        // Store demo token for testing
        if (data.reset_token) {
          setResetToken(data.reset_token);
        }
      } else {
        setError(data.detail || 'Failed to send reset email');
      }
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex">
        <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary-600 via-primary-700 to-primary-900 flex-col justify-center items-center p-12">
          <div className="max-w-md text-center">
            <div className="flex justify-center mb-8">
              <div className="w-20 h-20 bg-white/10 rounded-2xl flex items-center justify-center backdrop-blur-sm">
                <TrendingUp className="w-10 h-10 text-white" />
              </div>
            </div>
            <h1 className="text-4xl font-bold text-white mb-4">EasyTrade</h1>
            <p className="text-primary-100 text-lg">Professional algorithmic trading platform</p>
          </div>
        </div>

        <div className="flex-1 flex items-center justify-center p-8 bg-surface-50">
          <div className="w-full max-w-md">
            <div className="bg-white rounded-2xl shadow-card border border-surface-200 p-8 text-center">
              <div className="flex justify-center mb-6">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                  <CheckCircle className="w-8 h-8 text-green-600" />
                </div>
              </div>
              <h2 className="text-2xl font-bold text-surface-900 mb-4">Check Your Email</h2>
              <p className="text-surface-600 mb-6">
                We've sent password reset instructions to <strong>{email}</strong>
              </p>
              <p className="text-sm text-surface-500 mb-6">
                If you don't see the email, check your spam folder.
              </p>
              <Button onClick={() => navigate('/login')} className="w-full">
                Back to Login
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary-600 via-primary-700 to-primary-900 flex-col justify-center items-center p-12">
        <div className="max-w-md text-center">
          <div className="flex justify-center mb-8">
            <div className="w-20 h-20 bg-white/10 rounded-2xl flex items-center justify-center backdrop-blur-sm">
              <TrendingUp className="w-10 h-10 text-white" />
            </div>
          </div>
          <h1 className="text-4xl font-bold text-white mb-4">EasyTrade</h1>
          <p className="text-primary-100 text-lg">Professional algorithmic trading platform</p>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-8 bg-surface-50">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center justify-center gap-3 mb-8">
            <div className="w-12 h-12 bg-primary-600 rounded-xl flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-surface-900">EasyTrade</span>
          </div>

          <div className="bg-white rounded-2xl shadow-card border border-surface-200 p-8">
            <button 
              onClick={() => navigate('/login')}
              className="flex items-center gap-2 text-sm text-surface-600 hover:text-surface-900 mb-6"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Login
            </button>

            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-surface-900">Forgot Password?</h2>
              <p className="text-surface-500 mt-2">Enter your email to reset your password</p>
            </div>

            {error && (
              <div className="flex items-center gap-3 p-4 mb-6 bg-red-50 rounded-lg border border-red-200">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <Input
                type="email"
                label="Email address"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                leftIcon={<Mail className="w-5 h-5" />}
                required
              />

              <Button type="submit" className="w-full" size="lg" isLoading={loading}>
                Send Reset Link
              </Button>
            </form>

            <p className="text-center text-sm text-surface-500 mt-6">
              Remember your password?{' '}
              <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ForgotPasswordPage;
