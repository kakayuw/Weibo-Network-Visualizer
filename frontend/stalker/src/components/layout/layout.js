import React from 'react';
import 'antd/dist/antd.css';
import './layout.css';
import NetworkCanvas from '../canvas/canvas'
import { Layout, Menu, Breadcrumb } from 'antd';
import { UserOutlined, LaptopOutlined, NotificationOutlined } from '@ant-design/icons';

const { SubMenu } = Menu;
const { Header, Content, Footer, Sider } = Layout;

export default class PlatLayout extends React.Component {
    render() {
        return ( 
            <Layout style={{minHeight:'100%'}}>
            <Header className="header">
              <div className="logo" />
              <Menu theme="dark" mode="horizontal" defaultSelectedKeys={['2']}>
                <Menu.Item key="1">nav 1</Menu.Item>
                <Menu.Item key="2">nav 2</Menu.Item>
                <Menu.Item key="3">nav 3</Menu.Item>
              </Menu>
            </Header>
            <Content style={{ padding: '0 50px', minHeight:'100%'}}>
              <Breadcrumb style={{ margin: '16px 0' }}>
                <Breadcrumb.Item>Home</Breadcrumb.Item>
                <Breadcrumb.Item>List</Breadcrumb.Item>
                <Breadcrumb.Item>App</Breadcrumb.Item>
              </Breadcrumb>
              <Layout className="site-layout-background" style={{ padding: '24px 0' }}>
                <Sider className="site-layout-background" width={200}>
                  <Menu
                    mode="inline"
                    defaultSelectedKeys={['1']}
                    defaultOpenKeys={['sub1']}
                    style={{ height: '100%' }}
                  >
                    <SubMenu key="sub1" icon={<UserOutlined />} title="subnav 1">
                      <Menu.Item key="1">option1</Menu.Item>
                      <Menu.Item key="2">option2</Menu.Item>
                      <Menu.Item key="3">option3</Menu.Item>
                      <Menu.Item key="4">option4</Menu.Item>
                    </SubMenu>
                    <SubMenu key="sub2" icon={<LaptopOutlined />} title="subnav 2">
                      <Menu.Item key="5">option5</Menu.Item>
                      <Menu.Item key="6">option6</Menu.Item>
                      <Menu.Item key="7">option7</Menu.Item>
                      <Menu.Item key="8">option8</Menu.Item>
                    </SubMenu>
                    <SubMenu key="sub3" icon={<NotificationOutlined />} title="subnav 3">
                      <Menu.Item key="9">option9</Menu.Item>
                      <Menu.Item key="10">option10</Menu.Item>
                      <Menu.Item key="11">option11</Menu.Item>
                      <Menu.Item key="12">option12</Menu.Item>
                    </SubMenu>
                  </Menu>
                </Sider>
                <Content style={{ padding: '0 24px', minHeight: 400 }}>
                  <NetworkCanvas/>
                </Content>
              </Layout>
            </Content>
            <Footer style={{ textAlign: 'center' }}>Stalker@Drake</Footer>
          </Layout>
        );
    }
}