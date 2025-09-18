import React from 'react';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/Auth/ProtectedRoute';
import { UserProfile } from './components/Auth/UserProfile';
import { Whiteboard } from './components/Whiteboard';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <ProtectedRoute>
          <div className="min-h-screen bg-gray-100">
            <div className="container mx-auto px-4 py-4">
              <div className="flex justify-between items-center mb-6">
                <h1 className="text-3xl font-bold text-gray-900">
                  Multi-Galaxy-Note
                </h1>
                <UserProfile />
              </div>
              
              <div className="bg-white rounded-lg shadow-lg p-6">
                <h2 className="text-xl font-semibold text-gray-800 mb-4">
                  Digital Whiteboard
                </h2>
                <div className="whiteboard-wrapper" style={{ height: '70vh' }}>
                  <Whiteboard 
                    width={1200} 
                    height={800} 
                    className="w-full h-full"
                  />
                </div>
              </div>
            </div>
          </div>
        </ProtectedRoute>
      </div>
    </AuthProvider>
  );
}

export default App;
