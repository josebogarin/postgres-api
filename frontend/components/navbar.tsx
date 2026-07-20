/**
 * Barra de navegación
 */

'use client';

import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <nav className="bg-slate-900 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 font-bold text-xl">
            <span className="text-blue-400">📊</span> Sistema Admin BD
          </Link>

          {/* Navigation Links */}
          <div className="hidden md:flex gap-6">
            {user ? (
              <>
                <Link href="/dashboard" className="hover:text-blue-300 transition">
                  Dashboard
                </Link>
                <Link href="/applications" className="hover:text-blue-300 transition">
                  Aplicaciones
                </Link>
                <Link href="/users" className="hover:text-blue-300 transition">
                  Usuarios
                </Link>
                <Link href="/audit-logs" className="hover:text-blue-300 transition">
                  Auditoría
                </Link>
              </>
            ) : null}
          </div>

          {/* User Menu */}
          <div className="flex items-center gap-4">
            {user ? (
              <>
                <div className="text-sm">
                  <p className="font-semibold">{user.full_name || user.email}</p>
                  <p className="text-gray-400 text-xs">{user.email}</p>
                </div>
                <button
                  onClick={logout}
                  className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded transition"
                >
                  Salir
                </button>
              </>
            ) : (
              <Link href="/login" className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded transition">
                Iniciar Sesión
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
