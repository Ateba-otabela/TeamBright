export default function RevenueChart() {
  return (
    <article className="revenue-card">
      <div className="revenue-heading"><div><h2>Direct Revenue Over Time (XAF)</h2><p>Comparing B2C fan sales & tickets vs. B2B bounties & direct bookings (Last 30 Days)</p></div><div className="chart-legend"><span><i className="solid" />B2C Fan Sales</span><span><i className="dashed" />B2B Bookings</span></div></div>
      <svg className="revenue-chart" viewBox="0 0 760 250" role="img" aria-label="Direct revenue line chart">
        <g className="grid-lines"><line x1="48" y1="20" x2="740" y2="20"/><line x1="48" y1="75" x2="740" y2="75"/><line x1="48" y1="130" x2="740" y2="130"/><line x1="48" y1="185" x2="740" y2="185"/><line x1="48" y1="220" x2="740" y2="220"/></g>
        <defs><linearGradient id="revenueFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#f4c430" stopOpacity=".28"/><stop offset="1" stopColor="#f4c430" stopOpacity="0"/></linearGradient></defs>
        <path d="M55,190 C120,175 180,145 245,120 C310,95 370,110 435,72 C500,35 570,58 635,40 C680,28 715,24 740,22 L740,220 L55,220 Z" fill="url(#revenueFill)"/>
        <path className="b2c-line" d="M55,190 C120,175 180,145 245,120 C310,95 370,110 435,72 C500,35 570,58 635,40 C680,28 715,24 740,22" fill="none"/>
        <path className="b2b-line" d="M55,205 C120,198 180,190 245,172 C310,160 370,168 435,142 C500,126 570,132 635,112 C680,104 715,98 740,94" fill="none"/>
        <circle cx="435" cy="72" r="5" fill="#f4c430" stroke="#1a1607" strokeWidth="2"/><circle cx="740" cy="22" r="5" fill="#f4c430" stroke="#1a1607" strokeWidth="2"/>
        <g className="chart-labels"><text x="0" y="24">120k</text><text x="0" y="79">90k</text><text x="0" y="134">60k</text><text x="0" y="189">30k</text><text x="0" y="224">0</text><text x="50" y="242">Oct 24</text><text x="235" y="242">Nov 01</text><text x="420" y="242">Nov 10</text><text x="615" y="242">Nov 18</text><text x="700" y="242">Nov 23</text></g>
      </svg>
    </article>
  )
}
