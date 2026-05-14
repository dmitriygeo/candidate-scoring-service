export default function Spinner({ size = 'md', className = '' }) {
  const sizes = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4',
  };

  return (
    <div className={`flex items-center justify-center p-8 ${className}`}>
      <div 
        className={`${sizes[size]} border-gray-200 border-t-primary-600 rounded-full animate-spin`}
        style={{ borderTopColor: '#2563eb' }}
      />
    </div>
  );
}





