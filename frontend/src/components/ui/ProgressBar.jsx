const colors = {
  blue: 'bg-blue-500',
  green: 'bg-green-500',
  yellow: 'bg-yellow-500',
  red: 'bg-red-500',
  purple: 'bg-purple-500',
  pink: 'bg-pink-500',
  cyan: 'bg-cyan-500',
  orange: 'bg-orange-500',
  gray: 'bg-gray-500',
};

export default function ProgressBar({ value, color = 'blue', showLabel = false, className = '' }) {
  const percentage = Math.max(0, Math.min(100, value * 100));
  
  return (
    <div className={`relative ${className}`}>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div 
          className={`h-full ${colors[color]} transition-all duration-500 ease-out`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <span className="absolute right-0 -top-5 text-xs text-gray-500">
          {percentage.toFixed(0)}%
        </span>
      )}
    </div>
  );
}





