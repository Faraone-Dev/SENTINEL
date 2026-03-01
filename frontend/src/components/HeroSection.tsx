import React, { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Shield } from 'lucide-react';

// Particles Background
export const ParticlesBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const particles: { x: number; y: number; vx: number; vy: number; size: number; opacity: number }[] = [];
    for (let i = 0; i < 80; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        size: Math.random() * 2 + 0.5,
        opacity: Math.random() * 0.5 + 0.2,
      });
    }

    let animId: number;
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 255, 209, ${p.opacity})`;
        ctx.fill();
      });
      particles.forEach((p1, i) => {
        particles.slice(i + 1).forEach((p2) => {
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(0, 255, 209, ${0.1 * (1 - dist / 120)})`;
            ctx.stroke();
          }
        });
      });
      animId = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animId);
    };
  }, []);

  return <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none" />;
};

// Curved Text - Simple arc above shield
export const CurvedText: React.FC = () => {
  return (
    <svg viewBox="0 0 500 100" className="w-full h-full">
      <defs>
        <path id="curve" d="M 50,90 Q 250,10 450,90" fill="transparent" />
        <linearGradient id="textGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#00ffd1" />
          <stop offset="50%" stopColor="#00d4ff" />
          <stop offset="100%" stopColor="#0066ff" />
        </linearGradient>
      </defs>
      <text
        fill="url(#textGradient)"
        fontSize="48"
        fontWeight="bold"
        fontFamily="monospace"
        style={{ filter: 'drop-shadow(0 0 20px rgba(0, 255, 209, 0.9))' }}
      >
        <textPath href="#curve" startOffset="50%" textAnchor="middle">
          SENTINEL
        </textPath>
      </text>
    </svg>
  );
};

// Animated Shield
export const AnimatedShield: React.FC = () => (
  <div className="relative w-32 h-32 md:w-40 md:h-40">
    <motion.div
      className="absolute inset-0 rounded-full"
      style={{
        background: 'radial-gradient(circle, rgba(0, 255, 209, 0.3) 0%, transparent 70%)',
      }}
      animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.8, 0.5] }}
      transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
    />
    <div className="absolute inset-0 flex items-center justify-center">
      <Shield
        className="w-16 h-16 md:w-20 md:h-20"
        style={{
          color: '#00ffd1',
          filter: 'drop-shadow(0 0 20px rgba(0, 255, 209, 0.8)) drop-shadow(0 0 40px rgba(0, 255, 209, 0.4))',
        }}
      />
    </div>
  </div>
);

// Feature Card
export const FeatureCard: React.FC<{
  icon: React.ElementType;
  title: string;
  description: string;
  delay: number;
}> = ({ icon: Icon, title, description, delay }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.6, delay }}
    whileHover={{ scale: 1.02, y: -4 }}
    className="relative p-5 rounded-xl bg-slate-800/40 border border-slate-700/50 backdrop-blur-sm hover:border-cyan-500/30 transition-all duration-300 group"
  >
    <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-cyan-500/5 to-blue-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
    <div className="relative">
      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20 flex items-center justify-center mb-3">
        <Icon className="w-5 h-5 text-cyan-400" />
      </div>
      <h3 className="text-base font-semibold text-white mb-1">{title}</h3>
      <p className="text-sm text-slate-400 leading-relaxed">{description}</p>
    </div>
  </motion.div>
);
