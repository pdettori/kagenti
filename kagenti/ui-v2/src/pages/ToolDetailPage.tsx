// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  PageSection,
  Title,
  Breadcrumb,
  BreadcrumbItem,
  Spinner,
  EmptyState,
  EmptyStateHeader,
  EmptyStateIcon,
  EmptyStateBody,
  Button,
  DescriptionList,
  DescriptionListGroup,
  DescriptionListTerm,
  DescriptionListDescription,
  Label,
  Card,
  CardTitle,
  CardBody,
  Tabs,
  Tab,
  TabTitleText,
  Alert,
  Grid,
  GridItem,
  ClipboardCopy,
  Split,
  SplitItem,
  Flex,
  FlexItem,
  ExpandableSection,
  Modal,
  ModalVariant,
  Form,
  FormGroup,
  TextInput,
  Switch,
  FormHelperText,
  HelperText,
  HelperTextItem,
} from '@patternfly/react-core';
import {
  Table,
  Thead,
  Tr,
  Th,
  Tbody,
  Td,
} from '@patternfly/react-table';
import { ToolboxIcon, PlayIcon } from '@patternfly/react-icons';
import { useQuery, useMutation } from '@tanstack/react-query';

import { toolService } from '@/services/api';

interface StatusCondition {
  type: string;
  status: string;
  reason?: string;
  message?: string;
  lastTransitionTime?: string;
}

interface MCPToolInfo {
  name: string;
  description?: string;
  input_schema?: JSONSchema;
}

interface JSONSchema {
  type?: string;
  properties?: Record<string, JSONSchemaProperty>;
  required?: string[];
}

interface JSONSchemaProperty {
  type?: string;
  description?: string;
  default?: unknown;
  enum?: unknown[];
}

interface InvokeResult {
  content?: Array<{ type: string; text?: string; data?: unknown; value?: string }>;
  isError?: boolean;
}

export const ToolDetailPage: React.FC = () => {
  const { namespace, name } = useParams<{ namespace: string; name: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = React.useState<string | number>(0);
  const [expandedTools, setExpandedTools] = React.useState<Record<string, boolean>>({});

  // Invoke tool state
  const [invokeModalOpen, setInvokeModalOpen] = React.useState(false);
  const [selectedTool, setSelectedTool] = React.useState<MCPToolInfo | null>(null);
  const [toolArgs, setToolArgs] = React.useState<Record<string, unknown>>({});
  const [invokeResult, setInvokeResult] = React.useState<InvokeResult | null>(null);

  const { data: tool, isLoading, isError, error } = useQuery({
    queryKey: ['tool', namespace, name],
    queryFn: () => toolService.get(namespace!, name!),
    enabled: !!namespace && !!name,
    refetchInterval: (query) => {
      // Poll every 5 seconds if tool is not ready
      const status = query.state.data?.status || {};
      const phase = status.phase || '';
      const conditions = status.conditions || [];
      const isReady = phase === 'Running' || conditions.some(
        (c: { type: string; status: string }) => c.type === 'Ready' && c.status === 'True'
      );
      return isReady ? false : 5000;
    },
  });

  const connectMutation = useMutation({
    mutationFn: () => toolService.connect(namespace!, name!),
  });

  const invokeMutation = useMutation({
    mutationFn: ({ toolName, args }: { toolName: string; args: Record<string, unknown> }) =>
      toolService.invoke(namespace!, name!, toolName, args),
    onSuccess: (data) => {
      setInvokeResult(data.result as InvokeResult);
    },
  });

  // Open invoke modal for a specific tool
  const openInvokeModal = (mcpTool: MCPToolInfo) => {
    setSelectedTool(mcpTool);
    setInvokeResult(null);
    // Initialize args with default values from schema
    const initialArgs: Record<string, unknown> = {};
    if (mcpTool.input_schema?.properties) {
      Object.entries(mcpTool.input_schema.properties).forEach(([key, prop]) => {
        if (prop.default !== undefined) {
          initialArgs[key] = prop.default;
        } else if (prop.type === 'boolean') {
          initialArgs[key] = false;
        } else if (prop.type === 'number' || prop.type === 'integer') {
          initialArgs[key] = 0;
        } else {
          initialArgs[key] = '';
        }
      });
    }
    setToolArgs(initialArgs);
    setInvokeModalOpen(true);
  };

  // Close invoke modal
  const closeInvokeModal = () => {
    setInvokeModalOpen(false);
    setSelectedTool(null);
    setToolArgs({});
    invokeMutation.reset();
  };

  // Handle tool invocation
  const handleInvoke = () => {
    if (selectedTool) {
      invokeMutation.mutate({ toolName: selectedTool.name, args: toolArgs });
    }
  };

  // Update a single argument value
  const updateArg = (key: string, value: unknown) => {
    setToolArgs((prev) => ({ ...prev, [key]: value }));
  };

  if (isLoading) {
    return (
      <PageSection>
        <div className="kagenti-loading-center">
          <Spinner size="lg" aria-label="Loading tool details" />
        </div>
      </PageSection>
    );
  }

  if (isError || !tool) {
    return (
      <PageSection>
        <EmptyState>
          <EmptyStateHeader
            titleText="Tool not found"
            icon={<EmptyStateIcon icon={ToolboxIcon} />}
            headingLevel="h4"
          />
          <EmptyStateBody>
            {error instanceof Error
              ? error.message
              : `Could not load tool "${name}" in namespace "${namespace}".`}
          </EmptyStateBody>
          <Button variant="primary" onClick={() => navigate('/tools')}>
            Back to Tool Catalog
          </Button>
        </EmptyState>
      </PageSection>
    );
  }

  const metadata = tool.metadata || {};
  const spec = tool.spec || {};
  const status = tool.status || {};
  const labels = metadata.labels || {};
  const conditions: StatusCondition[] = status.conditions || [];

  // MCPServer CRD uses status.phase for ready state, not conditions
  const phase = status.phase || '';
  const isReady = phase === 'Running' || conditions.some(
    (c) => c.type === 'Ready' && c.status === 'True'
  );

  const toolUrl = `http://${name}.${namespace}.localtest.me:8080`;

  const toggleToolExpanded = (toolName: string) => {
    setExpandedTools((prev) => ({
      ...prev,
      [toolName]: !prev[toolName],
    }));
  };

  const mcpTools: MCPToolInfo[] = connectMutation.data?.tools || [];

  return (
    <>
      <PageSection variant="light">
        <Breadcrumb>
          <BreadcrumbItem
            to="/tools"
            onClick={(e) => {
              e.preventDefault();
              navigate('/tools');
            }}
          >
            Tool Catalog
          </BreadcrumbItem>
          <BreadcrumbItem isActive>{name}</BreadcrumbItem>
        </Breadcrumb>
        <Split hasGutter style={{ marginTop: '16px' }}>
          <SplitItem>
            <Title headingLevel="h1">{name}</Title>
          </SplitItem>
          <SplitItem>
            <Label color={isReady ? 'green' : 'red'}>
              {isReady ? 'Ready' : 'Not Ready'}
            </Label>
          </SplitItem>
          <SplitItem isFilled />
          <SplitItem>
            <Flex>
              <FlexItem>
                <Label color="blue">
                  {labels['kagenti.io/protocol']?.toUpperCase() || 'MCP'}
                </Label>
              </FlexItem>
            </Flex>
          </SplitItem>
        </Split>
      </PageSection>

      <PageSection>
        <Tabs
          activeKey={activeTab}
          onSelect={(_e, key) => setActiveTab(key)}
          aria-label="Tool details tabs"
        >
          <Tab eventKey={0} title={<TabTitleText>Details</TabTitleText>}>
            <Grid hasGutter style={{ marginTop: '16px' }}>
              <GridItem md={6}>
                <Card>
                  <CardTitle>Tool Information</CardTitle>
                  <CardBody>
                    <DescriptionList isCompact>
                      <DescriptionListGroup>
                        <DescriptionListTerm>Name</DescriptionListTerm>
                        <DescriptionListDescription>
                          {metadata.name}
                        </DescriptionListDescription>
                      </DescriptionListGroup>
                      <DescriptionListGroup>
                        <DescriptionListTerm>Namespace</DescriptionListTerm>
                        <DescriptionListDescription>
                          {metadata.namespace}
                        </DescriptionListDescription>
                      </DescriptionListGroup>
                      <DescriptionListGroup>
                        <DescriptionListTerm>Description</DescriptionListTerm>
                        <DescriptionListDescription>
                          {spec.description || 'No description available'}
                        </DescriptionListDescription>
                      </DescriptionListGroup>
                      <DescriptionListGroup>
                        <DescriptionListTerm>Created</DescriptionListTerm>
                        <DescriptionListDescription>
                          {metadata.creationTimestamp
                            ? new Date(metadata.creationTimestamp).toLocaleString()
                            : 'N/A'}
                        </DescriptionListDescription>
                      </DescriptionListGroup>
                      <DescriptionListGroup>
                        <DescriptionListTerm>UID</DescriptionListTerm>
                        <DescriptionListDescription>
                          <code style={{ fontSize: '0.85em' }}>
                            {metadata.uid || 'N/A'}
                          </code>
                        </DescriptionListDescription>
                      </DescriptionListGroup>
                    </DescriptionList>
                  </CardBody>
                </Card>
              </GridItem>

              <GridItem md={6}>
                <Card>
                  <CardTitle>Endpoint</CardTitle>
                  <CardBody>
                    <DescriptionList isCompact>
                      <DescriptionListGroup>
                        <DescriptionListTerm>MCP Server URL</DescriptionListTerm>
                        <DescriptionListDescription>
                          <ClipboardCopy isReadOnly hoverTip="Copy" clickTip="Copied">
                            {toolUrl}
                          </ClipboardCopy>
                        </DescriptionListDescription>
                      </DescriptionListGroup>
                    </DescriptionList>
                  </CardBody>
                </Card>
              </GridItem>
            </Grid>
          </Tab>

          <Tab eventKey={1} title={<TabTitleText>Status</TabTitleText>}>
            <Card style={{ marginTop: '16px' }}>
              <CardTitle>Status Conditions</CardTitle>
              <CardBody>
                {conditions.length === 0 ? (
                  <Alert variant="info" title="No status conditions available" isInline />
                ) : (
                  <Table aria-label="Status conditions" variant="compact">
                    <Thead>
                      <Tr>
                        <Th>Type</Th>
                        <Th>Status</Th>
                        <Th>Reason</Th>
                        <Th>Message</Th>
                        <Th>Last Transition</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {conditions.map((condition, index) => (
                        <Tr key={`${condition.type}-${index}`}>
                          <Td dataLabel="Type">{condition.type}</Td>
                          <Td dataLabel="Status">
                            <Label
                              color={condition.status === 'True' ? 'green' : 'red'}
                              isCompact
                            >
                              {condition.status}
                            </Label>
                          </Td>
                          <Td dataLabel="Reason">{condition.reason || '-'}</Td>
                          <Td dataLabel="Message">
                            {condition.message || '-'}
                          </Td>
                          <Td dataLabel="Last Transition">
                            {condition.lastTransitionTime
                              ? new Date(condition.lastTransitionTime).toLocaleString()
                              : '-'}
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                )}
              </CardBody>
            </Card>
          </Tab>

          <Tab eventKey={2} title={<TabTitleText>MCP Tools</TabTitleText>}>
            <Card style={{ marginTop: '16px' }}>
              <CardTitle>
                <Split hasGutter>
                  <SplitItem>Available MCP Tools</SplitItem>
                  <SplitItem isFilled />
                  <SplitItem>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => connectMutation.mutate()}
                      isLoading={connectMutation.isPending}
                      isDisabled={!isReady}
                    >
                      {connectMutation.isPending ? 'Connecting...' : 'Connect & List Tools'}
                    </Button>
                  </SplitItem>
                </Split>
              </CardTitle>
              <CardBody>
                {!isReady ? (
                  <Alert variant="warning" title="Tool not ready" isInline>
                    The MCP server must be ready before you can list available tools.
                  </Alert>
                ) : connectMutation.isError ? (
                  <Alert variant="danger" title="Connection failed" isInline>
                    {connectMutation.error instanceof Error
                      ? connectMutation.error.message
                      : 'Failed to connect to MCP server'}
                  </Alert>
                ) : mcpTools.length === 0 ? (
                  <Alert variant="info" title="No tools loaded" isInline>
                    Click "Connect & List Tools" to discover available MCP tools from this server.
                  </Alert>
                ) : (
                  <div>
                    {mcpTools.map((mcpTool) => (
                      <ExpandableSection
                        key={mcpTool.name}
                        toggleText={mcpTool.name}
                        isExpanded={expandedTools[mcpTool.name] || false}
                        onToggle={() => toggleToolExpanded(mcpTool.name)}
                        style={{ marginBottom: '8px' }}
                      >
                        <Card isFlat>
                          <CardBody>
                            <DescriptionList isCompact>
                              <DescriptionListGroup>
                                <DescriptionListTerm>Description</DescriptionListTerm>
                                <DescriptionListDescription>
                                  {mcpTool.description || 'No description'}
                                </DescriptionListDescription>
                              </DescriptionListGroup>
                              {mcpTool.input_schema && (
                                <DescriptionListGroup>
                                  <DescriptionListTerm>Input Schema</DescriptionListTerm>
                                  <DescriptionListDescription>
                                    <pre
                                      style={{
                                        backgroundColor: 'var(--pf-v5-global--BackgroundColor--200)',
                                        padding: '8px',
                                        borderRadius: '4px',
                                        fontSize: '0.8em',
                                        overflow: 'auto',
                                        maxHeight: '200px',
                                      }}
                                    >
                                      {JSON.stringify(mcpTool.input_schema, null, 2)}
                                    </pre>
                                  </DescriptionListDescription>
                                </DescriptionListGroup>
                              )}
                            </DescriptionList>
                            <Button
                              variant="secondary"
                              size="sm"
                              style={{ marginTop: '12px' }}
                              icon={<PlayIcon />}
                              onClick={() => openInvokeModal(mcpTool)}
                            >
                              Invoke Tool
                            </Button>
                          </CardBody>
                        </Card>
                      </ExpandableSection>
                    ))}
                  </div>
                )}
              </CardBody>
            </Card>
          </Tab>

          <Tab eventKey={3} title={<TabTitleText>YAML</TabTitleText>}>
            <Card style={{ marginTop: '16px' }}>
              <CardBody>
                <pre
                  style={{
                    backgroundColor: 'var(--pf-v5-global--BackgroundColor--200)',
                    padding: '16px',
                    borderRadius: '4px',
                    overflow: 'auto',
                    maxHeight: '500px',
                    fontSize: '0.85em',
                  }}
                >
                  {JSON.stringify(tool, null, 2)}
                </pre>
              </CardBody>
            </Card>
          </Tab>
        </Tabs>
      </PageSection>

      {/* Invoke Tool Modal */}
      <Modal
        variant={ModalVariant.medium}
        title={`Invoke: ${selectedTool?.name || ''}`}
        isOpen={invokeModalOpen}
        onClose={closeInvokeModal}
        actions={[
          <Button
            key="invoke"
            variant="primary"
            onClick={handleInvoke}
            isLoading={invokeMutation.isPending}
            isDisabled={invokeMutation.isPending}
            icon={<PlayIcon />}
          >
            {invokeMutation.isPending ? 'Invoking...' : 'Invoke'}
          </Button>,
          <Button key="cancel" variant="link" onClick={closeInvokeModal}>
            Close
          </Button>,
        ]}
      >
        {selectedTool && (
          <>
            {selectedTool.description && (
              <p style={{ marginBottom: '16px', color: 'var(--pf-v5-global--Color--200)' }}>
                {selectedTool.description}
              </p>
            )}

            <Form>
              {selectedTool.input_schema?.properties &&
              Object.keys(selectedTool.input_schema.properties).length > 0 ? (
                Object.entries(selectedTool.input_schema.properties).map(([key, prop]) => {
                  const isRequired = selectedTool.input_schema?.required?.includes(key);
                  const propType = prop.type || 'string';

                  return (
                    <FormGroup
                      key={key}
                      label={key}
                      isRequired={isRequired}
                      fieldId={`arg-${key}`}
                    >
                      {propType === 'boolean' ? (
                        <Switch
                          id={`arg-${key}`}
                          isChecked={toolArgs[key] as boolean}
                          onChange={(_e, checked) => updateArg(key, checked)}
                          label="true"
                          labelOff="false"
                        />
                      ) : propType === 'number' || propType === 'integer' ? (
                        <TextInput
                          id={`arg-${key}`}
                          type="number"
                          value={String(toolArgs[key] || '')}
                          onChange={(_e, val) => updateArg(key, val ? Number(val) : 0)}
                        />
                      ) : prop.enum ? (
                        <TextInput
                          id={`arg-${key}`}
                          value={String(toolArgs[key] || '')}
                          onChange={(_e, val) => updateArg(key, val)}
                          placeholder={`Options: ${prop.enum.join(', ')}`}
                        />
                      ) : (
                        <TextInput
                          id={`arg-${key}`}
                          value={String(toolArgs[key] || '')}
                          onChange={(_e, val) => updateArg(key, val)}
                        />
                      )}
                      {prop.description && (
                        <FormHelperText>
                          <HelperText>
                            <HelperTextItem>{prop.description}</HelperTextItem>
                          </HelperText>
                        </FormHelperText>
                      )}
                    </FormGroup>
                  );
                })
              ) : (
                <Alert variant="info" title="No arguments required" isInline>
                  This tool does not require any input arguments.
                </Alert>
              )}
            </Form>

            {/* Error display */}
            {invokeMutation.isError && (
              <Alert
                variant="danger"
                title="Invocation failed"
                isInline
                style={{ marginTop: '16px' }}
              >
                {invokeMutation.error instanceof Error
                  ? invokeMutation.error.message
                  : 'An unexpected error occurred'}
              </Alert>
            )}

            {/* Result display */}
            {invokeResult && (
              <div style={{ marginTop: '16px' }}>
                <Title headingLevel="h4" size="md" style={{ marginBottom: '8px' }}>
                  Result
                </Title>
                {invokeResult.isError && (
                  <Alert variant="warning" title="Tool returned an error" isInline isPlain />
                )}
                <pre
                  style={{
                    backgroundColor: invokeResult.isError
                      ? 'var(--pf-v5-global--danger-color--100)'
                      : 'var(--pf-v5-global--BackgroundColor--200)',
                    color: invokeResult.isError ? '#fff' : 'inherit',
                    padding: '12px',
                    borderRadius: '4px',
                    overflow: 'auto',
                    maxHeight: '300px',
                    fontSize: '0.85em',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {invokeResult.content?.map((item) => {
                    if (item.type === 'text' && item.text) {
                      return item.text;
                    }
                    if (item.type === 'data' && item.data) {
                      return JSON.stringify(item.data, null, 2);
                    }
                    if (item.value) {
                      return item.value;
                    }
                    return JSON.stringify(item, null, 2);
                  }).join('\n') || JSON.stringify(invokeResult, null, 2)}
                </pre>
              </div>
            )}
          </>
        )}
      </Modal>
    </>
  );
};
