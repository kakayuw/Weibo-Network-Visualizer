import React from 'react';
import 'antd/dist/antd.css';
import './canvas.css';
import { Layout, Menu, Breadcrumb, Input, Button, Tooltip, Row, Col  } from 'antd';
import * as d3 from 'd3'
import { UserOutlined, LaptopOutlined, NotificationOutlined } from '@ant-design/icons';

const { SubMenu } = Menu;
const { Header, Content, Footer, Sider } = Layout;
const { Search } = Input;

const style = { margin: '20px 20px 20px 20px' };
const url_prefix = "http://localhost:5000/double/";

export default class NetworkCanvas extends React.Component {

  trigger(url) {
    url = (typeof url !== "undefined") ? url : "http://localhost:5000/double/2478462555";
    // "svg"
    var svg = d3.select(this.refs.canvas)        
                // .attr("preserveAspectRatio", "xMinYMin meet")
                // .attr("viewBox", "-480 -300 960 600")
                ,
    width = +svg.attr("width"),
    height = +svg.attr("height");

    // remove previous elements
    svg.selectAll("*").remove()
  
    var color = d3.scaleOrdinal(d3.schemeCategory20);
  
    // form legend
    svg.append("circle").attr("cx",160).attr("cy",80).attr("r", 6).style("fill", color(0))
    svg.append("circle").attr("cx",160).attr("cy",110).attr("r", 6).style("fill", color(1))
    svg.append("circle").attr("cx",160).attr("cy",140).attr("r", 6).style("fill", color(2))
    svg.append("circle").attr("cx",160).attr("cy",170).attr("r", 6).style("fill", color(3))
    svg.append("text").attr("x", 180).attr("y", 80).text("You").style("font-size", "15px").attr("alignment-baseline","middle")
    svg.append("text").attr("x", 180).attr("y", 110).text("Following").style("font-size", "15px").attr("alignment-baseline","middle")
    svg.append("text").attr("x", 180).attr("y", 140).text("Following & Fan").style("font-size", "15px").attr("alignment-baseline","middle")
    svg.append("text").attr("x", 180).attr("y", 170).text("Fan").style("font-size", "15px").attr("alignment-baseline","middle")
  
    // build the arrow.
    svg.append("svg:defs").selectAll("marker")
        .data(["end"])      // Different link/path types can be defined here
      .enter().append("svg:marker")    // This section adds in the arrows
        .attr("id", String)
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 20)
        .attr("refY", -1.5)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .attr("xoverflow", "visible")
      .append("svg:path")
        .attr("d", "M0,-5L10,0L0,5");
  
    var repelForce = d3.forceManyBody().strength(-100).distanceMin(60);
  
    var simulation = d3.forceSimulation()
        .force("link", d3.forceLink().id(function(d) { return d.id; }))
        .force("repelForce", repelForce)
        .force("charge", d3.forceCollide().radius(10))
        .force("r", d3.forceRadial(function(d) { return d.layer * 150; }))
        .force("center", d3.forceCenter(width / 2, height / 2));
  
    d3.json(url, function(error, graph) {
      if (error) throw error;
  
      var link = svg.append("g")
        .attr("class", "links")
        .selectAll("line")
        .data(graph.links)
        .enter().append("line")
        //.attr("stroke-width", function(d) { return d.value; })
        .style("stroke", function(d) { return color(d.value); });
        //.attr("marker-end", "url(#end)");
  
      var node = svg.append("g")
          .attr("class", "nodes")
        .selectAll("g")
        .data(graph.nodes)
        .enter()
        .append("circle")
        .attr("r", function(d) { return Math.log2(d.size); })
        .attr("fill", function(d) { return color(d.group); })
        .style("opacity", function(d) { return 1 - (d.layer * 0.2) })
        .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));
  
  
    /* disabled text labels
      var lables = node.append("text")
          .text(function(d) {
            return d.id;
          })
          .attr('x', 6)
          .attr('y', 3);*/
  
      node.append("title")
          .text(function(d) { return d.id; });
  
      simulation
          .nodes(graph.nodes)
          .on("tick", ticked);
  
      simulation.force("link")
          .links(graph.links);
  
      function ticked() {
        link
            .attr("x1", function(d) { return d.source.x; })
            .attr("y1", function(d) { return d.source.y; })
            .attr("x2", function(d) { return d.target.x; })
            .attr("y2", function(d) { return d.target.y; });
  
        node
            .attr("transform", function(d) {
              return "translate(" + d.x + "," + d.y + ")";
            })
      }
    });
  
    function dragstarted(d) {
      if (!d3.event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }
  
    function dragged(d) {
      d.fx = d3.event.x;
      d.fy = d3.event.y;
    }
  
    function dragended(d) {
      if (!d3.event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }
  }

  componentDidMount() {
    this.trigger()
  }

  render() {
    return (
      <Layout  className="canvas-background">
        <Row gutter={16}>
          <Col span={8} style={style}>
          <Search
            placeholder="Type weibo id"
            enterButton="Search"
            size="large"
            onSearch={value => this.trigger(url_prefix+value)}
          />
          </Col>
          <Col span={8}></Col>
          <Col span={8}></Col>
        </Row>

        <svg width="960" height="600" ref="canvas"></svg>    
      </Layout>
      );
  }
}