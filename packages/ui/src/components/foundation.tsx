import * as React from 'react';
import { useWebSocket } from '@api-clients/ws-client';
import { cn } from '@utils/cn';

export const Button = React.forwardRef<HTMLButtonElement, {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  className?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading,
      className,
      children,
      ...props
    },
    ref,
  ) => (
    <button
      ref={ref}
      {...props}
      className={cn(
        'inline-flex items-center justify-center font-medium transition-all focus:outline-none',
        'focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed',
        variant === 'primary' && 'bg-primary-500 text-gray-900 hover:bg-primary-600',
        variant === 'secondary' && 'bg-gray-700 text-white hover:bg-gray-600',
        variant === 'danger' && 'bg-red-500 text-white hover:bg-red-600',
        size === 'sm'
          ? 'px-3 py-1.5 text-sm'
          : size === 'lg'
          ? 'px-6 py-3 text-lg'
          : 'px-4 py-2 text-base',
        className,
      )}
    >
      {isLoading && <span className="mr-2 animate-spin">⏳</span>}
      {children}
    </button>
  ),
);
Button.displayName = 'Button';

export const WidgetFrame: React.FC<{
  title: string;
  wsChannels?: string[];
  defaultCollapsed?: boolean;
  rightSlot?: React.ReactNode;
  errorMessage?: string;
  onRetry?: () => void;
}> = ({
  title,
  wsChannels = [],
  defaultCollapsed = false,
  rightSlot,
  errorMessage,
  onRetry,
  children,
}) => {
  const [isCollapsed, setCollapsed] = React.useState(defaultCollapsed);
  const ws = useWebSocket();

  React.useEffect(() => {
    if (!wsChannels.length) return;
    if (isCollapsed) {
      wsChannels.forEach((ch) => ws.unsubscribe(ch));
    } else {
      wsChannels.forEach((ch) => ws.subscribe(ch, () => {}));
    }
    return () => {
      wsChannels.forEach((ch) => ws.unsubscribe(ch));
    };
  }, [isCollapsed, ws, wsChannels]);

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 shadow-lg">
      <div className="flex items-center justify-between p-3 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          {errorMessage && (
            <span className="text-xs text-red-400 bg-red-400/10 px-2 py-1 rounded">Error</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {rightSlot}
          <button
            aria-label={isCollapsed ? 'Expand widget' : 'Collapse widget'}
            onClick={() => setCollapsed((v) => !v)}
            className="text-gray-400 hover:text-white p-1 rounded hover:bg-gray-700"
          >
            {isCollapsed ? '⊕' : '⊖'}
          </button>
        </div>
      </div>
      {!isCollapsed && (
        <div className="p-4">
          {errorMessage ? (
            <div className="text-center py-8">
              <div className="text-red-400 mb-2">{errorMessage}</div>
              {onRetry && (
                <Button variant="secondary" onClick={onRetry}>
                  Retry
                </Button>
              )}
            </div>
          ) : (
            children
          )}
        </div>
      )}
    </div>
  );
};
