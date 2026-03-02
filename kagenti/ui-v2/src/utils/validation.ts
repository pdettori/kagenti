// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

/**
 * Validate environment variable name according to Kubernetes rules.
 *
 * Must start with a letter or underscore, followed by any combination
 * of letters, digits, or underscores.
 */
export const isValidEnvVarName = (name: string): boolean => {
  if (!name) return false;
  const pattern = /^[A-Za-z_][A-Za-z0-9_]*$/;
  return pattern.test(name);
};

/**
 * Validate container image matches [HOST[:PORT]/]NAMESPACE/REPOSITORY.
 *
 * Requires at least NAMESPACE/REPOSITORY (two segments). An optional
 * HOST[:PORT] prefix gives a maximum of three segments.
 */
export const isValidContainerImage = (image: string): boolean => {
  const parts = image.split('/');
  if (parts.length < 2 || parts.length > 3) return false;
  if (parts.some((p) => p.length === 0)) return false;

  const validSegment = /^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$/;

  if (parts.length === 3) {
    // First part is HOST[:PORT]
    if (!/^[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?(:[0-9]+)?$/.test(parts[0])) return false;
    return validSegment.test(parts[1]) && validSegment.test(parts[2]);
  }

  // Two parts: NAMESPACE/REPOSITORY
  return validSegment.test(parts[0]) && validSegment.test(parts[1]);
};

/**
 * Validate an image tag.
 *
 * Must be valid ASCII containing only letters, digits, underscores,
 * periods, and dashes. May not start with a period or a dash.
 */
export const isValidImageTag = (tag: string): boolean => {
  if (!tag) return false;
  return /^[a-zA-Z0-9_][a-zA-Z0-9._-]*$/.test(tag);
};
