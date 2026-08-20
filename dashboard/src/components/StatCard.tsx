import React from 'react';
import { LucideIcon } from 'lucide-react';
import { Card, CardContent } from './ui/card';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  unit?: string;
  icon?: LucideIcon;
  trend?: {
    value: number | string;
    isPositive: boolean;
    label?: string;
  };
  baseline?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  unit,
  icon: Icon,
  trend,
  baseline,
}) => {
  return (
    <Card className="hover:border-muted-foreground/30 transition-colors">
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium text-muted-foreground">{title}</p>
          {Icon && <Icon className="w-4 h-4 text-muted-foreground" />}
        </div>
        
        <div className="mt-2 flex items-baseline gap-1.5">
          <span className="text-2xl font-bold tracking-tight text-foreground">
            {value}
          </span>
          {unit && <span className="text-xs font-medium text-muted-foreground">{unit}</span>}
        </div>

        {(subtitle || trend || baseline) && (
          <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
            {subtitle && <span>{subtitle}</span>}
            {trend && (
              <span
                className={`font-medium ml-auto flex items-center gap-0.5 ${
                  trend.isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
                }`}
              >
                {trend.isPositive ? '↑' : '↓'} {trend.value}
                {trend.label && <span className="text-muted-foreground ml-1">({trend.label})</span>}
              </span>
            )}
            {baseline && !trend && <span className="ml-auto text-muted-foreground">{baseline}</span>}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
