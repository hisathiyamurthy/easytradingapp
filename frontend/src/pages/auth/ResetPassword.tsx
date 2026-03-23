import { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { TrendingUp, Lock, ArrowLeft, AlertCircle, CheckCircle } from 'lucide-react';
import { Input, Button } from '@/components/ui';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    
    if (!token) {
      setError('Reset token is missing. Please use the link from your email.');
      return;
    }
    
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          token,
          new_password: password,
          confirm_password: confirmPassword 
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setSuccess(true);
      } else {
        setError(data.detail || 'Failed to reset password');
      }
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8 bg-surface-50">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-2xl shadow-card border border-surface-200 p-8 text-center">
            <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-surface-900 mb-4">Invalid Link</h2>
            <p className="text-surface-600 mb-6">
              This password reset link is invalid or missing. Please request a new password reset.
            </p>
            <Link to="/forgot-password" className="text-primary-600 hover:text-primary-700 font-medium">
              Request New Reset Link
            </Link>
          </div>
        </div>
      </div>
    );
  }

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
              <h2 className="text-2xl font-bold text-surface-900 mb-4">Password Reset!</h2>
              <p className="text-surface-600 mb-6">
                Your password has been reset successfully.
              </p>
              <Link 
                to="/login" 
                className="inline-flex items-center justify-center font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 px-6 py-3"
              >
                Go to Login
              </Link>
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
            <Link 
              to="/forgot-password" 
              className="flex items-center gap-2 text-sm text-surface-600 hover:text-surface-900 mb-6"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </Link>

            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Lock className="w-8 h-8 text-blue-600" />
              </div>
              <h2 className="text-2xl font-bold text-surface-900">Reset Password</h2>
              <p className="text-surface-500 mt-2">Enter your new password</p>
            </div>

            {error && (
              <div className="flex items-center gap-3 p-4 mb-6 bg-red-50 rounded-lg border border-red-200">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <Input
                type="password"
                label="New Password"
                placeholder="Enter new password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                leftIcon={<Lock className="w-5 h-5" />}
                required
              />

              <Input
                type="password"
                label="Confirm Password"
                placeholder="Confirm new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                leftIcon={<Lock className="w-5 h-5" />}
                required
              />

              <Button type="submit" className="w-full" size="lg" isLoading={loading}>
                Reset Password
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

export default ResetPasswordPage;
