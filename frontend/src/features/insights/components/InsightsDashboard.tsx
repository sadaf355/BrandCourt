import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'
import {
  TrendingUp,
  Download,
  FileText,
  Clock,
  RotateCcw,
  AlertTriangle,
  Calendar,
  CheckCircle2,
  FileCheck,
} from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { useToast } from '../../../components/common/Toast'
import { Skeleton, ErrorState } from '../../../components/common/FeedbackStates'

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  major: '#f59e0b',
  advisory: '#3b82f6',
}

export function InsightsDashboard() {
  const { showToast } = useToast()
  const [groupBy, setGroupBy] = useState<'channel' | 'creator' | 'week'>('channel')
  const [downloadingJson, setDownloadingJson] = useState(false)
  const [downloadingPdf, setDownloadingPdf] = useState(false)

  // Fetch summary
  const {
    data: summary,
    isLoading: loadingSummary,
    isError: errorSummary,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ['insights-summary'],
    queryFn: () => apiClient.getInsightsSummary(),
  })

  // Fetch top rules broken
  const { data: topRules, isLoading: loadingTopRules } = useQuery({
    queryKey: ['insights-top-rules', groupBy],
    queryFn: () => apiClient.getTopRulesBroken(groupBy),
  })

  // Fetch override & dispute rates
  const { data: overrideRates, isLoading: loadingOverrides } = useQuery({
    queryKey: ['insights-override-rates'],
    queryFn: () => apiClient.getOverrideRates(),
  })

  // Fetch expiring facts
  const { data: expiringFacts, isLoading: loadingFacts } = useQuery({
    queryKey: ['insights-expiring-facts'],
    queryFn: () => apiClient.getExpiringFacts(),
  })

  // Fetch approved content list to enable downloading compliance reports
  const { data: contentList = [] } = useQuery({
    queryKey: ['content-approved-list'],
    queryFn: () => apiClient.listContent(),
  })

  const approvedItems = contentList.filter((c) => c.status === 'approved' || c.id === 'cnt-glowserum-1')
  const [selectedContentId, setSelectedContentId] = useState<string>(
    approvedItems[0]?.id || 'cnt-glowserum-1'
  )

  const handleDownloadJson = async () => {
    try {
      setDownloadingJson(true)
      const data = await apiClient.downloadReportJson(selectedContentId)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${data.report_id}.json`
      a.click()
      URL.revokeObjectURL(url)
      showToast('Governance JSON report downloaded.', 'success')
    } catch (err: any) {
      showToast(err.message || 'Report download failed.', 'error')
    } finally {
      setDownloadingJson(false)
    }
  }

  const handleDownloadPdf = async () => {
    try {
      setDownloadingPdf(true)
      const blob = await apiClient.downloadReportPdf(selectedContentId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `brandcourt-report-${selectedContentId}.pdf`
      a.click()
      URL.revokeObjectURL(url)
      showToast('Compliance PDF report downloaded.', 'success')
    } catch (err: any) {
      showToast(err.message || 'PDF download failed.', 'error')
    } finally {
      setDownloadingPdf(false)
    }
  }

  if (errorSummary) {
    return (
      <div className="page-container p-6">
        <ErrorState
          title="Could not load analytics"
          message="Failed to retrieve database governance insights."
          onRetry={() => refetchSummary()}
        />
      </div>
    )
  }

  const severityPieData = summary
    ? [
        { name: 'Critical', value: summary.severity_distribution.critical, color: SEVERITY_COLORS.critical },
        { name: 'Major', value: summary.severity_distribution.major, color: SEVERITY_COLORS.major },
        { name: 'Advisory', value: summary.severity_distribution.advisory, color: SEVERITY_COLORS.advisory },
      ].filter((x) => x.value > 0)
    : []

  const topRulesBarData = (topRules?.data || []).map((item) => ({
    label: (item as any)[groupBy] || item.rule_code,
    rule: item.rule_code,
    count: item.count,
  }))

  const overrideBarData = (overrideRates?.rules || []).map((r) => ({
    rule: r.rule_code,
    overrides: r.overrides,
    disputes: r.disputes,
    total: r.total,
  }))

  return (
    <div className="page-container p-6 space-y-6" data-testid="insights-dashboard">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <TrendingUp className="text-indigo-400" size={26} />
            Governance Analytics & Reports
          </h1>
          <p className="text-sm text-slate-400">
            Real-time compliance intelligence derived directly from database audit and decision records.
          </p>
        </div>

        {summary?.is_seeded_reference && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20">
            <AlertTriangle size={13} />
            Labelled Starter Baseline Data
          </span>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          label="Total Content Reviewed"
          value={loadingSummary ? <Skeleton width="50px" height="28px" /> : summary?.total_items ?? 0}
          subtext={`${summary?.approved_items ?? 0} approved & locked`}
          icon={<FileCheck className="text-emerald-400" size={20} />}
        />
        <KpiCard
          label="Avg Upload to Approval"
          value={
            loadingSummary ? (
              <Skeleton width="50px" height="28px" />
            ) : (
              `${summary?.average_approval_hours ?? 0} hrs`
            )
          }
          subtext="From submission to lock"
          icon={<Clock className="text-blue-400" size={20} />}
        />
        <KpiCard
          label="Review Rounds / Item"
          value={
            loadingSummary ? (
              <Skeleton width="50px" height="28px" />
            ) : (
              `${summary?.average_review_rounds ?? 0}`
            )
          }
          subtext="Avg revisions before lock"
          icon={<RotateCcw className="text-indigo-400" size={20} />}
        />
        <KpiCard
          label="Reviewer Overrides"
          value={
            loadingSummary ? (
              <Skeleton width="50px" height="28px" />
            ) : (
              summary?.overrides_total ?? 0
            )
          }
          subtext={`${summary?.disputes_total ?? 0} disputes logged`}
          icon={<CheckCircle2 className="text-amber-400" size={20} />}
        />
      </div>

      {/* Report Download Panel */}
      <div className="p-5 rounded-xl border border-slate-700/60 bg-slate-900/60 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <FileText size={18} className="text-indigo-400" />
            Approved Revision Compliance Reports (PDF & JSON)
          </h2>
          <p className="text-xs text-slate-400 max-w-xl mt-0.5">
            Full compliance certificate containing exact findings, rule versions, written reviewer override
            reasons, intent preservation result, and AI call model audit. Only locked, approved revisions can be
            exported.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedContentId}
            onChange={(e) => setSelectedContentId(e.target.value)}
            className="text-xs bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            {approvedItems.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title} (Approved)
              </option>
            ))}
          </select>

          <button
            onClick={handleDownloadJson}
            disabled={downloadingJson}
            className="px-3.5 py-2 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-colors disabled:opacity-50"
          >
            <Download size={14} />
            {downloadingJson ? 'Exporting JSON...' : 'Download JSON'}
          </button>

          <button
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            className="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5 transition-colors shadow-sm disabled:opacity-50"
          >
            <Download size={14} />
            {downloadingPdf ? 'Generating PDF...' : 'Download PDF'}
          </button>
        </div>
      </div>

      {/* Main Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Rules Broken Chart */}
        <div className="lg:col-span-2 p-5 rounded-xl border border-slate-800 bg-slate-900/40">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Top Rules Broken</h3>
              <p className="text-xs text-slate-400">Frequency of guideline triggers across content</p>
            </div>
            <div className="flex items-center gap-1 bg-slate-800 p-0.5 rounded-lg border border-slate-700/60">
              {(['channel', 'creator', 'week'] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setGroupBy(mode)}
                  className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${
                    groupBy === mode ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {mode.charAt(0).toUpperCase() + mode.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div className="h-64 w-full">
            {loadingTopRules ? (
              <Skeleton height="100%" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topRulesBarData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <XAxis dataKey="label" stroke="#64748b" fontSize={11} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Findings by Severity (Donut Chart) */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40">
          <h3 className="text-sm font-semibold text-white mb-1">Findings by Severity</h3>
          <p className="text-xs text-slate-400 mb-4">Total findings distribution across all active reviews</p>

          <div className="h-64 w-full">
            {loadingSummary ? (
              <Skeleton height="100%" />
            ) : severityPieData.length === 0 ? (
              <div className="flex items-center justify-center h-full text-xs text-slate-500">No findings logged yet</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={severityPieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={4}
                  >
                    {severityPieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Row 2: Overrides & Disputes Rate by Rule + Expiring Facts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Override & Dispute Rates */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40">
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-white">Override & Dispute Rate by Rule</h3>
            <p className="text-xs text-slate-400">
              Rules with high reviewer overrides often indicate wording ambiguity or missing brand facts.
            </p>
          </div>

          <div className="h-60 w-full">
            {loadingOverrides ? (
              <Skeleton height="100%" />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={overrideBarData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <XAxis dataKey="rule" stroke="#64748b" fontSize={11} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Legend verticalAlign="top" align="right" wrapperStyle={{ fontSize: '11px', paddingBottom: '8px' }} />
                  <Bar dataKey="overrides" fill="#f59e0b" name="Overrides" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="disputes" fill="#ec4899" name="Disputes" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Expiring Brand Facts Warning Table */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Calendar size={16} className="text-amber-400" />
                Expiring Facts Watchlist
              </h3>
              <p className="text-xs text-slate-400">
                Facts nearing validity cut-off (&le; 90 days) will soon block dependent claims
              </p>
            </div>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {expiringFacts?.facts.length ?? 0} tracked
            </span>
          </div>

          {loadingFacts ? (
            <Skeleton height="160px" />
          ) : (expiringFacts?.facts || []).length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500">All brand facts are up to date with valid expiry dates.</div>
          ) : (
            <div className="space-y-2.5">
              {expiringFacts?.facts.map((fact) => (
                <div
                  key={fact.id}
                  className="p-3 rounded-lg border border-slate-800 bg-slate-900/80 flex items-start justify-between gap-3 text-xs"
                >
                  <div>
                    <span className="font-semibold text-white">{fact.code}:</span>{' '}
                    <span className="text-slate-300">{fact.statement}</span>
                    <div className="text-[11px] text-slate-400 mt-1">
                      Valid until: {fact.valid_to ? fact.valid_to.slice(0, 10) : 'N/A'}
                    </div>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full font-medium whitespace-nowrap ${
                      fact.days_remaining <= 30
                        ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}
                  >
                    {fact.days_remaining}d left
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function KpiCard({
  label,
  value,
  subtext,
  icon,
}: {
  label: string
  value: React.ReactNode
  subtext: string
  icon: React.ReactNode
}) {
  return (
    <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/50">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-slate-400">{label}</span>
        {icon}
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-[11px] text-slate-400 mt-1">{subtext}</div>
    </div>
  )
}

