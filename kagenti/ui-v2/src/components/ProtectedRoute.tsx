// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import React from 'react';
import {
  Bullseye,
  Spinner,
  EmptyState,
  EmptyStateHeader,
  EmptyStateIcon,
  EmptyStateBody,
  EmptyStateFooter,
  EmptyStateActions,
  Button,
} from '@patternfly/react-core';
import { LockIcon } from '@patternfly/react-icons';

import { useAuth } from '@/contexts';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRoles?: string[];
}

/**
 * ProtectedRoute component that wraps routes requiring authentication.
 *
 * - Shows a loading spinner while auth state is being determined
 * - Shows login prompt if user is not authenticated
 * - Shows access denied if user lacks required roles
 * - Renders children if user is authenticated and authorized
 */
export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRoles = [],
}) => {
  const { isAuthenticated, isLoading, isEnabled, user, login } = useAuth();

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <Bullseye style={{ minHeight: '400px' }}>
        <Spinner size="xl" aria-label="Checking authentication..." />
      </Bullseye>
    );
  }

  // If auth is disabled, render children directly
  if (!isEnabled) {
    return <>{children}</>;
  }

  // Show login prompt if not authenticated
  if (!isAuthenticated) {
    return (
      <Bullseye style={{ minHeight: '400px' }}>
        <EmptyState>
          <EmptyStateHeader
            titleText="Authentication Required"
            icon={<EmptyStateIcon icon={LockIcon} />}
            headingLevel="h4"
          />
          <EmptyStateBody>
            You need to sign in to access this page. Click the button below to
            authenticate with Keycloak.
          </EmptyStateBody>
          <EmptyStateFooter>
            <EmptyStateActions>
              <Button variant="primary" onClick={login}>
                Sign In
              </Button>
            </EmptyStateActions>
          </EmptyStateFooter>
        </EmptyState>
      </Bullseye>
    );
  }

  // Check role-based access if requiredRoles specified
  if (requiredRoles.length > 0 && user) {
    const hasRequiredRole = requiredRoles.some((role) =>
      user.roles.includes(role)
    );

    if (!hasRequiredRole) {
      return (
        <Bullseye style={{ minHeight: '400px' }}>
          <EmptyState>
            <EmptyStateHeader
              titleText="Access Denied"
              icon={<EmptyStateIcon icon={LockIcon} />}
              headingLevel="h4"
            />
            <EmptyStateBody>
              You don't have permission to access this page. Required role(s):{' '}
              {requiredRoles.join(', ')}
            </EmptyStateBody>
          </EmptyState>
        </Bullseye>
      );
    }
  }

  // User is authenticated and authorized
  return <>{children}</>;
};
