// src/components/Header.tsx
import Link from 'next/link';

export default function Header() {
  return (
    <header className="w-full bg-gray-800 text-white p-4">
      <nav className="container mx-auto flex justify-between">
        <Link href="/" className="font-bold text-xl">
          Pearl Invest
        </Link>
        <div className="space-x-4">
          <Link href="/portfolio" className="hover:text-gray-300">Portfolio</Link>
          <Link href="/trading" className="hover:text-gray-300">Trading</Link>
          <Link href="/auth" className="hover:text-gray-300">Login</Link>
        </div>
      </nav>
    </header>
  );
}