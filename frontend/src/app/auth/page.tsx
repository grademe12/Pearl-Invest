'use client';

import { useState } from 'react';

// 라즈베리파이 K8s Auth 서비스 주소
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://192.168.45.205:30080';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState('');
  const [profile, setProfile] = useState<any>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // 로그인 테스트
  const handleLogin = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        throw new Error('Login failed');
      }

      const data = await response.json();
      setToken(data.access_token);
      
      // 토큰 로컬 스토리지 저장
      localStorage.setItem('token', data.access_token);
      
      alert('Login successful!');
      console.log('Token:', data.access_token);
      console.log('User:', data.username);
      console.log('Roles:', data.roles);
      
    } catch (err) {
      setError('Login failed. Check credentials.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // 프로필 조회 테스트
  const handleGetProfile = async () => {
    if (!token) {
      setError('Please login first');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_URL}/user/profile`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to get profile');
      }

      const data = await response.json();
      setProfile(data);
      
    } catch (err) {
      setError('Failed to get profile');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // 헬스체크
  const handleHealthCheck = async () => {
    try {
      const response = await fetch(`${API_URL}/health`);
      const data = await response.json();
      alert(`Service Status: ${data.status}\nService: ${data.service}`);
    } catch (err) {
      setError('Service is not reachable');
      console.error(err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-md mx-auto bg-white rounded-lg shadow-md p-6">
        <h1 className="text-2xl font-bold mb-6">Pearl Auth Test</h1>
        
        {/* Health Check */}
        <div className="mb-6">
          <button
            onClick={handleHealthCheck}
            className="w-full bg-green-500 text-white py-2 px-4 rounded hover:bg-green-600"
          >
            Check Service Health
          </button>
        </div>

        {/* Login Form */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full border rounded px-3 py-2"
              placeholder="admin, trader, or viewer"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border rounded px-3 py-2"
              placeholder="admin123, trader123, or viewer123"
            />
          </div>

          <button
            onClick={handleLogin}
            disabled={loading || !username || !password}
            className="w-full bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Login'}
          </button>
        </div>

        {/* Token Display */}
        {token && (
          <div className="mt-6 p-4 bg-gray-100 rounded">
            <p className="text-sm font-medium mb-2">Access Token:</p>
            <p className="text-xs break-all font-mono">{token}</p>
            
            <button
              onClick={handleGetProfile}
              className="mt-4 w-full bg-purple-500 text-white py-2 px-4 rounded hover:bg-purple-600"
            >
              Get Profile
            </button>
          </div>
        )}

        {/* Profile Display */}
        {profile && (
          <div className="mt-6 p-4 bg-blue-50 rounded">
            <p className="font-medium mb-2">User Profile:</p>
            <pre className="text-xs">{JSON.stringify(profile, null, 2)}</pre>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="mt-4 p-3 bg-red-100 text-red-700 rounded">
            {error}
          </div>
        )}

        {/* Test Accounts Info */}
        <div className="mt-6 p-4 bg-yellow-50 rounded">
          <p className="text-sm font-medium mb-2">Test Accounts:</p>
          <ul className="text-xs space-y-1">
            <li>admin / admin123</li>
            <li>trader / trader123</li>
            <li>viewer / viewer123</li>
          </ul>
        </div>
      </div>
    </div>
  );
}