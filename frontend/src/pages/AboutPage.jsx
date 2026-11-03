import PageHero from '../components/PageHero'

export default function AboutPage() {
  return (
    <>
      <PageHero
        title="About Nice Day Carwash"
        subtitle="Your trusted partner for premium car care in Iloilo City."
      />

      <section className="section">
        <div className="container">
          <div className="about-split">
            <div>
              <span className="eyebrow eyebrow-dark">Our story</span>
              <h2>A clean car makes for a nicer day.</h2>
              <p>
                Founded in Iloilo City, Nice Day Carwash combines quality, convenience
                and environmental responsibility. We believe every day should be a nice
                day, starting with a clean, well-maintained vehicle.
              </p>
            </div>
            <div className="about-highlight">
              <span className="highlight-icon">&#128663;</span>
              <h3>Premium car care</h3>
              <p>
                Careful hand washing, modern equipment and friendly service on every
                visit.
              </p>
            </div>
          </div>

          <div className="about-split">
            <div className="about-highlight">
              <span className="highlight-icon">&#127775;</span>
              <h3>Excellence in service</h3>
              <p>
                We pay attention to the details that make your vehicle feel brand new
                again.
              </p>
            </div>
            <div>
              <span className="eyebrow eyebrow-dark">Our mission</span>
              <h2>Exceptional service, every time.</h2>
              <p>
                Our mission is to exceed expectations while protecting the environment.
                From a quick rinse to a full detail, our team treats every vehicle with
                the same professional care.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="section section-alt">
        <div className="container">
          <div className="section-heading">
            <h2>Our values</h2>
            <p>The principles behind every wash.</p>
          </div>
          <div className="values-grid">
            <article className="value-card">
              <div className="value-icon">&#127919;</div>
              <h3>Quality</h3>
              <p>
                We never compromise on the quality of our service and always strive for
                perfection.
              </p>
            </article>
            <article className="value-card">
              <div className="value-icon">&#129309;</div>
              <h3>Trust</h3>
              <p>
                Reliable and honest service that builds lasting relationships with our
                customers.
              </p>
            </article>
            <article className="value-card">
              <div className="value-icon">&#127793;</div>
              <h3>Sustainability</h3>
              <p>
                Eco-friendly practices and products that help protect our environment.
              </p>
            </article>
            <article className="value-card">
              <div className="value-icon">&#9889;</div>
              <h3>Efficiency</h3>
              <p>
                Fast, professional service that respects your time without cutting
                corners.
              </p>
            </article>
          </div>
        </div>
      </section>
    </>
  )
}
