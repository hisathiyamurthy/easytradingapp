import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { TrendingUp, Mail, Lock, User, Phone, AlertCircle, CheckCircle } from 'lucide-react';
import { Input, Button } from '@/components/ui';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface FormData {
  email: string;
  password: string;
  confirm_password: string;
  first_name: string;
  last_name: string;
  phone: string;
}

interface FormErrors {
  email?: string;
  password?: string;
  confirm_password?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
}

export function RegisterPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [formData, setFormData] = useState<FormData>({
    email: '',
    password: '',
    confirm_password: '',
    first_name: '',
    last_name: '',
    phone: '',
  });

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.first_name.trim()) {
      newErrors.first_name = 'First name is required';
    }

    if (!formData.last_name.trim()) {
      newErrors.last_name = 'Last name is required';
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    } else if (!/[A-Z]/.test(formData.password)) {
      newErrors.password = 'Password must contain at least one uppercase letter';
    } else if (!/[a-z]/.test(formData.password)) {
      newErrors.password = 'Password must contain at least one lowercase letter';
    } else if (!/[0-9]/.test(formData.password)) {
      newErrors.password = 'Password must contain at least one number';
    }

    if (formData.password !== formData.confirm_password) {
      newErrors.confirm_password = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          confirm_password: formData.confirm_password,
          first_name: formData.first_name,
          last_name: formData.last_name,
          phone: formData.phone || null,
        }),
      });

      const data = await response.json();

      if (response.ok && response.status === 200) {
        setSuccess(true);
      } else {
        // Handle various error formats
        let errorMsg = 'Registration failed. Please try again.';
        if (typeof data.detail === 'string') {
          errorMsg = data.detail;
        } else if (Array.isArray(data.detail)) {
          errorMsg = data.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
        } else if (data.message) {
          errorMsg = data.message;
        }
        setError(errorMsg);
      }
    } catch (err: any) {
      console.error('Registration error:', err);
      setError('Network error. Please check your connection and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8 bg-surface-50">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-2xl shadow-card border border-surface-200 p-8 text-center">
            <div className="flex justify-center mb-6">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
            </div>
            <h2 className="text-2xl font-bold text-surface-900 mb-4">Registration Successful!</h2>
            <p className="text-surface-600 mb-6">
              Your account has been created and is pending approval by an administrator. 
              You will receive an email once your account is approved.
            </p>
            <div className="bg-surface-50 rounded-lg p-4 mb-6">
              <p className="text-sm text-surface-600">
                <strong>Next Steps:</strong>
              </p>
              <ul className="text-sm text-surface-600 mt-2 space-y-1">
                <li>1. Wait for admin approval</li>
                <li>2. You will receive an email notification</li>
                <li>3. Log in after approval</li>
              </ul>
            </div>
            <Button onClick={() => navigate('/login')} className="w-full">
              Go to Login
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary-600 via-primary-700 to-primary-900 flex-col justify-center items-center p-12">
        <div className="max-w-md text-center">
          <div className="flex justify-center mb-8">
            <div className="w-20 h-20 bg-white/10 rounded-2xl flex items-center justify-center backdrop-blur-sm">
              <TrendingUp className="w-10 h-10 text-white" />
            </div>
          </div>
          <h1 className="text-4xl font-bold text-white mb-4">EasyTrade</h1>
          <p className="text-primary-100 text-lg mb-8">
            Join thousands of traders using our professional algorithmic trading platform
          </p>
          <div className="grid grid-cols-2 gap-4 text-sm text-primary-100">
            <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
              <div className="text-2xl font-bold text-white">50+</div>
              <div>Technical Indicators</div>
            </div>
            <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
              <div className="text-2xl font-bold text-white">4</div>
              <div>Indian Brokers</div>
            </div>
            <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
              <div className="text-2xl font-bold text-white">99.9%</div>
              <div>Uptime SLA</div>
            </div>
            <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
              <div className="text-2xl font-bold text-white">Real-time</div>
              <div>Market Data</div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Side - Registration Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-surface-50">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-8">
            <div className="w-12 h-12 bg-primary-600 rounded-xl flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-surface-900">EasyTrade</span>
          </div>

          <div className="bg-white rounded-2xl shadow-card border border-surface-200 p-8">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-surface-900">Create Account</h2>
              <p className="text-surface-500 mt-2">Register for access to the trading platform</p>
            </div>

            {error && (
              <div className="flex items-center gap-3 p-4 mb-6 bg-red-50 rounded-lg border border-red-200">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="First Name"
                  placeholder="John"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  leftIcon={<User className="w-5 h-5" />}
                  error={errors.first_name}
                  required
                />

                <Input
                  label="Last Name"
                  placeholder="Doe"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  error={errors.last_name}
                  required
                />
              </div>

              <Input
                type="email"
                label="Email address"
                placeholder="name@example.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                leftIcon={<Mail className="w-5 h-5" />}
                error={errors.email}
                required
              />

              <Input
                type="tel"
                label="Phone Number (Optional)"
                placeholder="+91 9876543210"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                leftIcon={<Phone className="w-5 h-5" />}
                error={errors.phone}
              />

              <Input
                type="password"
                label="Password"
                placeholder="Create a strong password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                leftIcon={<Lock className="w-5 h-5" />}
                error={errors.password}
                helper="Min 8 chars with uppercase, lowercase, and number"
                required
              />

              <Input
                type="password"
                label="Confirm Password"
                placeholder="Confirm your password"
                value={formData.confirm_password}
                onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
                leftIcon={<Lock className="w-5 h-5" />}
                error={errors.confirm_password}
                required
              />

              <div className="bg-surface-50 rounded-lg p-4">
                <p className="text-sm text-surface-600">
                  <strong>Note:</strong> After registration, your account will require approval 
                  from an administrator before you can log in.
                </p>
              </div>

              <Button type="submit" className="w-full" size="lg" isLoading={isLoading}>
                Create Account
              </Button>
            </form>

            <p className="text-center text-sm text-surface-500 mt-6">
              Already have an account?{' '}
              <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
                Sign in
              </Link>
            </p>
          </div>

          <div className="mt-6 text-center">
            <Link to="/login" className="text-sm text-surface-500 hover:text-surface-700">
              ← Back to Login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default RegisterPage;
